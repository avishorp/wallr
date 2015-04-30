/* 
 * File:   opencv_modect.c
 * Author: lee@sodnpoo.com
 */

#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>

#include <opencv2/core/core.hpp>
#include "bcm_host.h"
#include "interface/vcos/vcos.h"

#include "interface/mmal/mmal.h"
#include "interface/mmal/util/mmal_default_components.h"
#include "interface/mmal/util/mmal_connection.h"
#include "interface/mmal/util/mmal_util_params.h"
#include "interface/mmal/util/mmal_util.h"

#include <python2.7/Python.h>
#include <numpy/ndarrayobject.h>

#define MMAL_CAMERA_PREVIEW_PORT 0
#define MMAL_CAMERA_VIDEO_PORT 1
#define MMAL_CAMERA_CAPTURE_PORT 2

#define CALC_FPS 1


#define DEFAULT_VIDEO_FPS 30 
#define DEFAULT_VIDEO_WIDTH 1280
#define DEFAULT_VIDEO_HEIGHT 720

using namespace cv;

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
 
} PORT_USERDATA;

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
      printf("  Frame = %d, Frame Post %d, Framerate = %.0f fps \n", frame_count, frame_post_count, fps);
    }
#endif // CALC_FPS

    // Copy the video frame to cvMat objects (one for each component)
    mmal_buffer_header_mem_lock(buffer);
    /*
    // Create component matrices
    unsigned char* pointer = (unsigned char *)(buffer -> data);
    Mat y(userdata->height, userdata->width, CV_8UC1, pointer);
    pointer = pointer + (userdata->height*userdata->width);
    Mat u(userdata->height/2, userdata->width/2, CV_8UC1, pointer);
    pointer = pointer + (userdata->height*userdata->width/4);
    Mat v(userdata->height/2, userdata->width/2, CV_8UC1, pointer);
    */

    mmal_buffer_header_mem_unlock(buffer);

#if 0
    //if(1){
    if(userdata->grabframe){
      mmal_buffer_header_mem_lock(buffer);
      
      //monkey with the imageData pointer, to avoid a memcpy
      char* oldImageData = userdata->stub->imageData;
      userdata->stub->imageData = buffer->data;
      cvResize(userdata->stub, userdata->small_image, CV_INTER_LINEAR);
      userdata->stub->imageData = oldImageData;
      
      mmal_buffer_header_mem_unlock(buffer);

      if (vcos_semaphore_trywait(&(userdata->complete_semaphore)) != VCOS_SUCCESS) {
        vcos_semaphore_post(&(userdata->complete_semaphore));
        frame_post_count++;
      }
    }

    //if(1){
    if( 0 && (frame_count % (userdata->fps * still_interval) == 0) ){ //every 60 seconds
      mmal_buffer_header_mem_lock(buffer);

      fprintf(stderr, "WRITING STILL (%d)\n", frame_count);
/*
      //Just grab the Y and write it out ASAP      
      //monkey with the imageData pointer, to avoid a memcpy
      char* oldImageData = userdata->stub->imageData;
      userdata->stub->imageData = buffer->data;

      //grab a still for export to www
      cvSaveImage("/home/pi/image.tmp.jpg", userdata->stub, 0);

      userdata->stub->imageData = oldImageData;
*/
/**/
      //TODO some of this can probably be collapsed down, but as we only do this once a minute I don't care so much....
      //so here we're going to attempt a new method to get full YUV
      unsigned char* pointer = (unsigned char *)(buffer -> data);
      //get Y U V as CvMat()s
      CvMat y = cvMat(userdata->height, userdata->width, CV_8UC1, pointer);
      pointer = pointer + (userdata->height*userdata->width);
      CvMat u = cvMat(userdata->height/2, userdata->width/2, CV_8UC1, pointer);
      pointer = pointer + (userdata->height*userdata->width/4);
      CvMat v = cvMat(userdata->height/2, userdata->width/2, CV_8UC1, pointer);
      //resize U and V and convert Y U and V into IplImages
      IplImage* uu = cvCreateImage(cvSize(userdata->width, userdata->height), IPL_DEPTH_8U, 1);
      cvResize(&u, uu, CV_INTER_LINEAR);
      IplImage* vv = cvCreateImage(cvSize(userdata->width, userdata->height), IPL_DEPTH_8U, 1);
      cvResize(&v, vv, CV_INTER_LINEAR);
      IplImage* yy = cvCreateImage(cvSize(userdata->width, userdata->height), IPL_DEPTH_8U, 1);
      cvResize(&y, yy, CV_INTER_LINEAR);
      //Create the final, 3 channel image      
      IplImage* image = cvCreateImage(cvSize(userdata->width, userdata->height), IPL_DEPTH_8U, 3);
      CvArr * output[] = { image };      
      //map Y to the 1st channel
      int from_to[] = {0, 0};
      const CvArr * inputy[] = { yy };
      cvMixChannels(inputy, 1, output, 1, from_to, 1);
      //map V to the 2nd channel
      from_to[1] = 1;
      const CvArr * inputv[] = { vv };
      cvMixChannels(inputv, 1, output, 1, from_to, 1);
      //map U to the 3rd channel
      from_to[1] = 2;
      const CvArr * inputu[] = { uu };
      cvMixChannels(inputu, 1, output, 1, from_to, 1);
      //convert the colour space      
      cvCvtColor(image, image, CV_YCrCb2BGR);
      //save the image
      cvSaveImage(STILL_TMPFN, image, 0);
      //cleanup the images
      cvReleaseImage(&yy);
      cvReleaseImage(&vv);
      cvReleaseImage(&uu);
      cvReleaseImage(&image);
/**/ 
      
      mmal_buffer_header_mem_unlock(buffer);


#endif
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

/**
 * Set the rotation of the image
 * @param camera Pointer to camera component
 * @param rotation Degree of rotation (any number, but will be converted to 0,90,180 or 270 only)
 * @return 0 if successful, non-zero if any parameters out of range
 */
int raspicamcontrol_set_rotation(MMAL_COMPONENT_T *camera, int rotation)
{
   int ret;
   int my_rotation = ((rotation % 360 ) / 90) * 90;

   ret = mmal_port_parameter_set_int32(camera->output[0], MMAL_PARAMETER_ROTATION, my_rotation);
   mmal_port_parameter_set_int32(camera->output[1], MMAL_PARAMETER_ROTATION, my_rotation);
   mmal_port_parameter_set_int32(camera->output[2], MMAL_PARAMETER_ROTATION, my_rotation);

   return ret;
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
        fprintf(stderr, "Error: create camera %x\n", status);
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
        fprintf(stderr, "Error: camera viewfinder format couldn't be set\n");
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

    fprintf(stderr, "camera video buffer_size = %d\n", camera_video_port->buffer_size);
    fprintf(stderr, "camera video buffer_num = %d\n", camera_video_port->buffer_num);

    status = mmal_port_format_commit(camera_video_port);
    if (status != MMAL_SUCCESS) {
        fprintf(stderr, "Error: unable to commit camera video port format (%u)\n", status);
        return -1;
    }

    camera_video_port_pool = (MMAL_POOL_T *) mmal_port_pool_create(camera_video_port, camera_video_port->buffer_num, camera_video_port->buffer_size);
    userdata->camera_video_port_pool = camera_video_port_pool;
    camera_video_port->userdata = (struct MMAL_PORT_USERDATA_T *) userdata;


    status = mmal_port_enable(camera_video_port, camera_video_buffer_callback);

    if (status != MMAL_SUCCESS) {
        fprintf(stderr, "Error: unable to enable camera video port (%u)\n", status);
        return -1;
    }

    status = mmal_component_enable(camera);
    if (status != MMAL_SUCCESS) {
        fprintf(stderr, "Error: unable to enable camera (%u)\n", status);
        return -1;
    }

    fill_port_buffer(userdata->camera_video_port, userdata->camera_video_port_pool);

    if (mmal_port_parameter_set_boolean(camera_video_port, MMAL_PARAMETER_CAPTURE, 1) != MMAL_SUCCESS) {
        printf("%s: Failed to start capture\n", __func__);
    }

    raspicamcontrol_set_rotation(camera, userdata->rotation);

    fprintf(stderr, "camera created\n");
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
        fprintf(stderr, "Error: unable to create preview (%u)\n", status);
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
        fprintf(stderr, "Error: unable to commit encoder input port format (%u)\n", status);
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
        fprintf(stderr, "Error: unable to commit encoder output port format (%u)\n", status);
        return -1;
    }

    fprintf(stderr, "encoder input buffer_size = %d\n", encoder_input_port->buffer_size);
    fprintf(stderr, "encoder input buffer_num = %d\n", encoder_input_port->buffer_num);

    fprintf(stderr, "encoder output buffer_size = %d\n", encoder_output_port->buffer_size);
    fprintf(stderr, "encoder output buffer_num = %d\n", encoder_output_port->buffer_num);

    encoder_input_port_pool = (MMAL_POOL_T *) mmal_port_pool_create(encoder_input_port, encoder_input_port->buffer_num, encoder_input_port->buffer_size);
    userdata->encoder_input_pool = encoder_input_port_pool;
    encoder_input_port->userdata = (struct MMAL_PORT_USERDATA_T *) userdata;
    status = mmal_port_enable(encoder_input_port, encoder_input_buffer_callback);
    if (status != MMAL_SUCCESS) {
        fprintf(stderr, "Error: unable to enable encoder input port (%u)\n", status);
        return -1;
    }
    fprintf(stderr, "encoder input pool has been created\n");

    encoder_output_port_pool = (MMAL_POOL_T *) mmal_port_pool_create(encoder_output_port, encoder_output_port->buffer_num, encoder_output_port->buffer_size);
    userdata->encoder_output_pool = encoder_output_port_pool;
    encoder_output_port->userdata = (struct MMAL_PORT_USERDATA_T *) userdata;

    status = mmal_port_enable(encoder_output_port, encoder_output_buffer_callback);
    if (status != MMAL_SUCCESS) {
        fprintf(stderr, "Error: unable to enable encoder output port (%u)\n", status);
        return -1;
    }
    fprintf(stderr, "encoder output pool has been created\n");    

    fill_port_buffer(encoder_output_port, encoder_output_port_pool);

    fprintf(stderr, "encoder has been created\n");
    return 0;
}

int main(int argc, char** argv) {
    PORT_USERDATA userdata;
    MMAL_STATUS_T status;
    memset(&userdata, 0, sizeof (PORT_USERDATA));

    userdata.width = DEFAULT_VIDEO_WIDTH;
    userdata.height = DEFAULT_VIDEO_HEIGHT;
    userdata.fps = DEFAULT_VIDEO_FPS;    

    int c;
    opterr = 0;


    fprintf(stderr, "VIDEO_WIDTH : %i\n", userdata.width );
    fprintf(stderr, "VIDEO_HEIGHT: %i\n", userdata.height );
    fprintf(stderr, "VIDEO_FPS   : %i\n", userdata.fps);

    bcm_host_init();

    if (1 && setup_camera(&userdata) != 0) {
        fprintf(stderr, "Error: setup camera %x\n", status);
        return -1;
    }

    if (1 && setup_encoder(&userdata) != 0) {
        fprintf(stderr, "Error: setup encoder %x\n", status);
        return -1;
    }

    vcos_semaphore_create(&userdata.complete_semaphore, "mmal_opencv_video", 0);
    /*
    IplImage* fore = NULL;
    IplImage* sub = NULL;
    IplImage* gray = NULL;

    sub = cvCreateImage(cvSize(userdata.opencv_width, userdata.opencv_height), IPL_DEPTH_8U, 1);
    back = cvCreateImage(cvSize(userdata.opencv_width, userdata.opencv_height), IPL_DEPTH_8U, 1);
    gray = cvCreateImage(cvSize(userdata.opencv_width, userdata.opencv_height), IPL_DEPTH_8U, 1);
    
    userdata.small_image = cvCreateImage(cvSize(userdata.opencv_width, userdata.opencv_height), IPL_DEPTH_8U, 1);
    userdata.stub = cvCreateImage(cvSize(userdata.width, userdata.height), IPL_DEPTH_8U, 1);
    */
    int count = 0;

    int opencv_frames = 0;
    struct timespec t1;
    struct timespec t2;
    clock_gettime(CLOCK_MONOTONIC, &t1);

    struct timespec s;
    s.tv_sec = 0;
    s.tv_nsec = 30000000;

    while (1) {

      //nanosleep(&s, NULL);

      if(1){
        if (vcos_semaphore_wait(&(userdata.complete_semaphore)) == VCOS_SUCCESS) {

	  //printf("frame\n");
	}

      }
    }

    return 0;
}



static PyObject * PyInit(PyObject *self, PyObject *args)
{
  int number;
  int sts;

  if (!PyArg_ParseTuple(args, "i", &number))
    return NULL;

  //  if (sts < 0) {
  //  PyErr_SetString(SpamError, "System command failed");
  //  return NULL;
  //}

  npy_intp dims[] = {5, 8};
  char* dat;
  dat = (char*)malloc(5*8);
  for(int kk=0; kk < dims[0]*dims[1]; kk++) dat[kk] = kk;


  int x = NPY_UINT8;
  //  PyObject* pp = PyArray_ZEROS(2, &dims, NPY_UINT8, 0);

  //PyObject* pp = PyArray_New(&PyArray_Type, 2, dims, NPY_UINT8, NULL, NULL, 0, NULL, NULL);
  PyObject* pp = PyArray_SimpleNewFromData(2, dims, NPY_UINT8, dat);

  return pp;
}

static PyMethodDef RaspicapMethods[] = {
    {"init",  PyInit, METH_VARARGS,
     "Initialize raspicap"},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

static PyObject* RaspicapError;

PyMODINIT_FUNC initraspicap()
{
  import_array();

  PyObject *m;

  m = Py_InitModule("raspicap", RaspicapMethods);
  if (m == NULL)
    return;

  RaspicapError = PyErr_NewException("raspicap.error", NULL, NULL);
  Py_INCREF(RaspicapError);
  PyModule_AddObject(m, "error", RaspicapError);
}
