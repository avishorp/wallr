/* 
 * File:   opencv_modect.c
 * Author: lee@sodnpoo.com
 */

#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>

#include "bcm_host.h"
#include "interface/vcos/vcos.h"

#include "interface/mmal/mmal.h"
#include "interface/mmal/util/mmal_default_components.h"
#include "interface/mmal/util/mmal_connection.h"
#include "interface/mmal/util/mmal_util_params.h"
#include "interface/mmal/util/mmal_util.h"

#include <Python.h>
#include <numpy/ndarrayobject.h>

#include "RaspiCamControl.h"

#define MMAL_CAMERA_PREVIEW_PORT 0
#define MMAL_CAMERA_VIDEO_PORT 1
#define MMAL_CAMERA_CAPTURE_PORT 2

#define CALC_FPS 0


#define DEFAULT_VIDEO_FPS 30 
#define DEFAULT_VIDEO_WIDTH 1280
#define DEFAULT_VIDEO_HEIGHT 720

typedef struct {
    int width;
    int height;
    int fps;
    
    MMAL_COMPONENT_T *camera;
    MMAL_COMPONENT_T *encoder;
    MMAL_COMPONENT_T *preview;

    MMAL_PORT_T *camera_video_port;
    MMAL_POOL_T *camera_video_port_pool;
    MMAL_PORT_T *encoder_input_port;
    MMAL_POOL_T *encoder_input_pool;
    MMAL_PORT_T *encoder_output_port;
    MMAL_POOL_T *encoder_output_pool;

    VCOS_SEMAPHORE_T complete_semaphore;
    
    float video_fps;  
    int rotation;

  PyObject* next_frame;
  bool next_frame_available;
  unsigned int frames_received;
  unsigned int frames_skipped;

  bool setup_done;
} PORT_USERDATA;


static PORT_USERDATA* g_userdata = NULL;
static char* g_error_message;

int fill_port_buffer(MMAL_PORT_T *port, MMAL_POOL_T *pool) {
    int q;
    int num = mmal_queue_length(pool->queue);

    for (q = 0; q < num; q++) {
        MMAL_BUFFER_HEADER_T *buffer = mmal_queue_get(pool->queue);
        if (!buffer) {
            fprintf(stderr, "Unable to get a required buffer %d from pool queue\n", q);
        }

        if (mmal_port_send_buffer(port, buffer) != MMAL_SUCCESS) {
            fprintf(stderr, "Unable to send a buffer to port (%d)\n", q);
        }
    }
}

static void camera_video_buffer_callback(MMAL_PORT_T *port, MMAL_BUFFER_HEADER_T *buffer) {
    PORT_USERDATA *userdata = (PORT_USERDATA *) port->userdata;

#ifdef CALC_FPS
    static struct timespec t1;
    struct timespec t2;

    static int frame_count = 0;
    static int frame_post_count = 0;

    if (frame_count == 0) {
        clock_gettime(CLOCK_MONOTONIC, &t1);
    }
    frame_count++;

    if( (frame_count % (userdata->fps*2)) == 0) { //every 2 seconds
      // print framerate every n frame
      clock_gettime(CLOCK_MONOTONIC, &t2);
      float d = (t2.tv_sec + t2.tv_nsec / 1000000000.0) - (t1.tv_sec + t1.tv_nsec / 1000000000.0);
      float fps = 0.0;

      if (d > 0) {
          fps = frame_count / d;
      } else {
          fps = frame_count;
      }
      userdata->video_fps = fps;
    }
#endif // CALC_FPS

    // Copy the video frame to cvMat objects (one for each component)
    mmal_buffer_header_mem_lock(buffer);

    userdata->frames_received++;
    if (!userdata->next_frame_available) {
      // Create a Python object holding the next frame
      // Y
      unsigned char* pointer = (unsigned char *)(buffer -> data);
      npy_intp dims[] = {userdata->height, userdata->width};
      PyObject* y = PyArray_SimpleNew(2, dims, NPY_UINT8);
      memcpy(PyArray_DATA(((PyArrayObject*)y)), pointer, dims[0]*dims[1]);

      // U
      dims[0] = userdata->height/2;
      dims[1] = userdata->height/2;
      pointer = pointer + (userdata->height*userdata->width);
      PyObject* u = PyArray_SimpleNew(2, dims, NPY_UINT8);
      memcpy(PyArray_DATA(((PyArrayObject*)u)), pointer, dims[0]*dims[1]);

      // V
      pointer = pointer + (userdata->height*userdata->width/4);
      PyObject* v = PyArray_SimpleNew(2, dims, NPY_UINT8);
      memcpy(PyArray_DATA(((PyArrayObject*)v)), pointer, dims[0]*dims[1]);

      // Create the frame tuple
      PyObject* pframe = PyTuple_New(3);
      PyTuple_SetItem(pframe, 0, y);
      PyTuple_SetItem(pframe, 1, u);
      PyTuple_SetItem(pframe, 2, v);

      // Set the frame available flag
      userdata->next_frame = pframe;
      userdata->next_frame_available = true;
    }
    else
      userdata->frames_skipped++;

    mmal_buffer_header_mem_unlock(buffer);

      if (vcos_semaphore_trywait(&(userdata->complete_semaphore)) != VCOS_SUCCESS) {
        vcos_semaphore_post(&(userdata->complete_semaphore));
        frame_post_count++;
      }


    mmal_buffer_header_release(buffer);

    // and send one back to the port (if still open)
    if (port->is_enabled) {
        MMAL_STATUS_T status;

        MMAL_BUFFER_HEADER_T *new_buffer;
        MMAL_POOL_T *pool = userdata->camera_video_port_pool;
        new_buffer = mmal_queue_get(pool->queue);

        if (new_buffer) {
            status = mmal_port_send_buffer(port, new_buffer);
        }

        if (!new_buffer || status != MMAL_SUCCESS) {
            fprintf(stderr, "[%s]Unable to return a buffer to the video port\n", __func__);
        }
    }
}

static void encoder_input_buffer_callback(MMAL_PORT_T *port, MMAL_BUFFER_HEADER_T *buffer) {
    mmal_buffer_header_release(buffer);
}

static void encoder_output_buffer_callback(MMAL_PORT_T *port, MMAL_BUFFER_HEADER_T *buffer) {
    mmal_buffer_header_release(buffer);
}

//TODO remove the preview port
int setup_camera(PORT_USERDATA *userdata) {

    MMAL_STATUS_T status;
    MMAL_COMPONENT_T *camera = 0;
    MMAL_ES_FORMAT_T *format;
    MMAL_PORT_T * camera_preview_port;
    MMAL_PORT_T * camera_video_port;
    MMAL_PORT_T * camera_still_port;
    MMAL_POOL_T * camera_video_port_pool;

    status = mmal_component_create(MMAL_COMPONENT_DEFAULT_CAMERA, &camera);
    if (status != MMAL_SUCCESS) {
        sprintf(g_error_message, "create camera %x\n", status);
        return -1;
    }
    userdata->camera = camera;
    userdata->camera_video_port = camera->output[MMAL_CAMERA_VIDEO_PORT];

    camera_preview_port = camera->output[MMAL_CAMERA_PREVIEW_PORT];
    camera_video_port = camera->output[MMAL_CAMERA_VIDEO_PORT];
    camera_still_port = camera->output[MMAL_CAMERA_CAPTURE_PORT];

    {

        MMAL_PARAMETER_CAMERA_CONFIG_T cam_config = {
	  { MMAL_PARAMETER_CAMERA_CONFIG, sizeof (cam_config)},  // hdr
	  userdata->width, // max_stills_w
          userdata->height, // max_stills_h
          0, // stills_yuv422
          1, // one_shot_stills
          userdata->width, // max_preview_video_w
          userdata->height, // max_preview_video_h
          3, // num_preview_video_frames
          0, // stills_capture_circular_buffer_height
          0, // fast_preview_resume
          MMAL_PARAM_TIMESTAMP_MODE_RESET_STC // use_stc_timestamp
        };
        mmal_port_parameter_set(camera->control, &cam_config.hdr);
    }

    // Setup camera preview port format 
    format = camera_preview_port->format;
    //format->encoding = MMAL_ENCODING_I420;
    format->encoding = MMAL_ENCODING_OPAQUE;
    format->encoding_variant = MMAL_ENCODING_I420;
    format->es->video.width = userdata->width;
    format->es->video.height = userdata->height;
    format->es->video.crop.x = 0;
    format->es->video.crop.y = 0;
    format->es->video.crop.width = userdata->width;
    format->es->video.crop.height = userdata->height;

    status = mmal_port_format_commit(camera_preview_port);

    if (status != MMAL_SUCCESS) {
        sprintf(g_error_message, "camera viewfinder format couldn't be set");
        return -1;
    }

    // Setup camera video port format
    mmal_format_copy(camera_video_port->format, camera_preview_port->format);

    format = camera_video_port->format;
    format->encoding = MMAL_ENCODING_I420;
    format->encoding_variant = MMAL_ENCODING_I420;
    format->es->video.width = userdata->width;
    format->es->video.height = userdata->height;
    format->es->video.crop.x = 0;
    format->es->video.crop.y = 0;
    format->es->video.crop.width = userdata->width;
    format->es->video.crop.height = userdata->height;
    format->es->video.frame_rate.num = userdata->fps;
    format->es->video.frame_rate.den = 1;

    camera_video_port->buffer_num = 2;
    camera_video_port->buffer_size = (format->es->video.width * format->es->video.height * 12 / 8 ) * camera_video_port->buffer_num;

    status = mmal_port_format_commit(camera_video_port);
    if (status != MMAL_SUCCESS) {
        sprintf(g_error_message, "Error: unable to commit camera video port format (%u)", status);
        return -1;
    }

    camera_video_port_pool = (MMAL_POOL_T *) mmal_port_pool_create(camera_video_port, camera_video_port->buffer_num, camera_video_port->buffer_size);
    userdata->camera_video_port_pool = camera_video_port_pool;
    camera_video_port->userdata = (struct MMAL_PORT_USERDATA_T *) userdata;


    status = mmal_port_enable(camera_video_port, camera_video_buffer_callback);

    if (status != MMAL_SUCCESS) {
        sprintf(g_error_message, "unable to enable camera video port (%u)", status);
        return -1;
    }

    status = mmal_component_enable(camera);
    if (status != MMAL_SUCCESS) {
        sprintf(g_error_message, "unable to enable camera (%u)", status);
        return -1;
    }

    fill_port_buffer(userdata->camera_video_port, userdata->camera_video_port_pool);

    if (mmal_port_parameter_set_boolean(camera_video_port, MMAL_PARAMETER_CAPTURE, 1) != MMAL_SUCCESS) {
        printf("%s: Failed to start capture\n", __func__);
    }

    return 0;
}

int setup_encoder(PORT_USERDATA *userdata) {
    MMAL_STATUS_T status;
    MMAL_COMPONENT_T *encoder = 0;
    MMAL_PORT_T *preview_input_port = NULL;

    MMAL_PORT_T *encoder_input_port = NULL, *encoder_output_port = NULL;
    MMAL_POOL_T *encoder_input_port_pool;
    MMAL_POOL_T *encoder_output_port_pool;

    status = mmal_component_create(MMAL_COMPONENT_DEFAULT_VIDEO_ENCODER, &encoder);
    if (status != MMAL_SUCCESS) {
        sprintf(g_error_message, "unable to create preview (%u)", status);
        return -1;
    }

    encoder_input_port = encoder->input[0];
    encoder_output_port = encoder->output[0];
    userdata->encoder_input_port = encoder_input_port;
    userdata->encoder_output_port = encoder_input_port;

    mmal_format_copy(encoder_input_port->format, userdata->camera_video_port->format);
    encoder_input_port->buffer_size = encoder_input_port->buffer_size_recommended;
    encoder_input_port->buffer_num = 2;

    mmal_format_copy(encoder_output_port->format, encoder_input_port->format);

    encoder_output_port->buffer_size = encoder_output_port->buffer_size_recommended;
    encoder_output_port->buffer_num = 2;
    // Commit the port changes to the input port 
    status = mmal_port_format_commit(encoder_input_port);
    if (status != MMAL_SUCCESS) {
        sprintf(g_error_message, "unable to commit encoder input port format (%u)", status);
        return -1;
    }

    // Only supporting H264 at the moment
    encoder_output_port->format->encoding = MMAL_ENCODING_H264;
    encoder_output_port->format->bitrate = 2000000;

    encoder_output_port->buffer_size = encoder_output_port->buffer_size_recommended;

    if (encoder_output_port->buffer_size < encoder_output_port->buffer_size_min) {
        encoder_output_port->buffer_size = encoder_output_port->buffer_size_min;
    }

    encoder_output_port->buffer_num = encoder_output_port->buffer_num_recommended;

    if (encoder_output_port->buffer_num < encoder_output_port->buffer_num_min) {
        encoder_output_port->buffer_num = encoder_output_port->buffer_num_min;
    }

    // Commit the port changes to the output port    
    status = mmal_port_format_commit(encoder_output_port);
    if (status != MMAL_SUCCESS) {
        printf(g_error_message, "unable to commit encoder output port format (%u)", status);
        return -1;
    }

    encoder_input_port_pool = (MMAL_POOL_T *) mmal_port_pool_create(encoder_input_port, encoder_input_port->buffer_num, encoder_input_port->buffer_size);
    userdata->encoder_input_pool = encoder_input_port_pool;
    encoder_input_port->userdata = (struct MMAL_PORT_USERDATA_T *) userdata;
    status = mmal_port_enable(encoder_input_port, encoder_input_buffer_callback);
    if (status != MMAL_SUCCESS) {
        sprintf(g_error_message, "unable to enable encoder input port (%u)", status);
        return -1;
    }

    encoder_output_port_pool = (MMAL_POOL_T *) mmal_port_pool_create(encoder_output_port, encoder_output_port->buffer_num, encoder_output_port->buffer_size);
    userdata->encoder_output_pool = encoder_output_port_pool;
    encoder_output_port->userdata = (struct MMAL_PORT_USERDATA_T *) userdata;

    status = mmal_port_enable(encoder_output_port, encoder_output_buffer_callback);
    if (status != MMAL_SUCCESS) {
        sprintf(g_error_message, "unable to enable encoder output port (%u)", status);
        return -1;
    }

    fill_port_buffer(encoder_output_port, encoder_output_port_pool);

    return 0;
}

void init_userdata(PORT_USERDATA& ud) {
  memset(&ud, 0, sizeof (PORT_USERDATA));

  ud.next_frame = (PyObject*)NULL;
  ud.next_frame_available = false;
  ud.frames_received = 0;
  ud.frames_skipped = 0;
}


///////////////////////////// PYTHON INTERFACE ////////////////////////////
///////////////////////////////////////////////////////////////////////////

static PyObject* g_raspicap_error;
static char* g_setup_keywords[] = {
  "width", "height", "fps", "saturation", "sharpness", "exposure", "awb", NULL
};
static bool g_setup_done;

static PyObject * py_setup(PyObject *self, PyObject *args, PyObject* kwds)
{
  MMAL_STATUS_T status;

  g_userdata->width = DEFAULT_VIDEO_WIDTH;
  g_userdata->height = DEFAULT_VIDEO_HEIGHT;
  g_userdata->fps = DEFAULT_VIDEO_FPS;    

  int saturation = 0;
  int sharpness = 0;
  char* exposure = NULL;
  char* awb = NULL;


  if (!PyArg_ParseTupleAndKeywords(args, kwds, "|iiiiiss", g_setup_keywords,
				   &g_userdata->width, &g_userdata->height, 
				   &g_userdata->fps, &saturation, &sharpness,
				   &exposure, &awb))
    return NULL;


  if (1 && setup_camera(g_userdata) != 0) {
    PyErr_SetString(g_raspicap_error, g_error_message);
    return NULL;
    }

  if (1 && setup_encoder(g_userdata) != 0) {
    PyErr_SetString(g_raspicap_error, g_error_message);
    return NULL;
  }

  // Set additional camera parameters
  raspicamcontrol_set_saturation(g_userdata->camera, saturation);
  raspicamcontrol_set_sharpness(g_userdata->camera, sharpness);
  // EXPOSURE
  if (exposure != NULL) {
    MMAL_PARAM_EXPOSUREMODE_T m;
    m = exposure_mode_from_string(exposure);

    if (m==-1) {
      PyErr_SetString(g_raspicap_error, "Invalid exposure specification");
      return NULL;
    }

    if (raspicamcontrol_set_exposure_mode(g_userdata->camera, m) != 0) {
      PyErr_SetString(g_raspicap_error, "Failed setting exposure mode");
      return NULL;
    }
  }
  // AWB
  if (awb != NULL) {
    MMAL_PARAM_AWBMODE_T m;
    m = awb_mode_from_string(exposure);

    if (m==-1) {
      PyErr_SetString(g_raspicap_error, "Invalid awb specification");
      return NULL;
    }

    if (raspicamcontrol_set_awb_mode(g_userdata->camera, m) != 0) {
      PyErr_SetString(g_raspicap_error, "Failed setting awb mode");
      return NULL;
    }
  }


  bcm_host_init();

  g_setup_done = true;

  Py_INCREF(Py_None);
  return Py_None;

}

static PyObject* py_next_frame(PyObject *self, PyObject *args)
{
  // Make sure the camera is set up
  if (!g_setup_done) {
    PyErr_SetString(g_raspicap_error, "Must setup camera before getting frames");
    return NULL;
  }

  // No arguments
  PyObject* ret;

  if (g_userdata->next_frame_available) {
    ret = g_userdata->next_frame;
    g_userdata->next_frame = NULL;
    g_userdata->next_frame_available = false;
  }
  else {
    Py_INCREF(Py_None);
    ret = Py_None;
  }

  return ret;
}

static PyObject* py_next_frame_block(PyObject *self, PyObject *args)
{
  // Make sure the camera is set up
  if (!g_setup_done) {
    PyErr_SetString(g_raspicap_error, "Must setup camera before getting frames");
    return NULL;
  }

  // Block until a frame is available
  while (!g_userdata->next_frame_available) {
      if (vcos_semaphore_wait(&(g_userdata->complete_semaphore)) != VCOS_SUCCESS) {
	// Problem, raise exception
      }
  }

  return py_next_frame(self, args);
}


static PyMethodDef g_raspicap_methods[] = {
  {"setup",  (PyCFunction)py_setup, METH_VARARGS|METH_KEYWORDS,
     "Setup camera"},
    {"next_frame", py_next_frame, METH_VARARGS,
     "Grab the next available frame, return None if no frame available"},
    {"next_frame_block", py_next_frame_block, METH_VARARGS,
     "Wait until a frame is available, then grab the next available frame"},

    {NULL, NULL, 0, NULL}        /* Sentinel */
};




PyMODINIT_FUNC initraspicap()
{
  g_setup_done = false;

  // Initialize NumPy
  import_array();

  // Create application-specific exception
  PyObject *m;

  m = Py_InitModule("raspicap", g_raspicap_methods);
  if (m == NULL)
    return;

  g_raspicap_error = PyErr_NewException("raspicap.error", NULL, NULL);
  Py_INCREF(g_raspicap_error);
  PyModule_AddObject(m, "error", g_raspicap_error);

  // Basic static initialization
  static PORT_USERDATA userdata;

  g_userdata = &userdata;
  init_userdata(userdata);
  vcos_semaphore_create(&userdata.complete_semaphore, "mmal_opencv_video", 0);



}




