/*
Copyright (c) 2013, Broadcom Europe Ltd
Copyright (c) 2013, James Hughes
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the copyright holder nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/


 //#include "interface/vcos/vcos.h"

 //#include "interface/vmcs_host/vc_vchi_gencmd.h"
#include "interface/mmal/mmal.h"
#include "interface/mmal/mmal_logging.h"
#include "interface/mmal/util/mmal_util.h"
#include "interface/mmal/util/mmal_util_params.h"
#include "interface/mmal/util/mmal_default_components.h"
#include "RaspiCamControl.h"


/// Cross reference structure, mode string against mode id
typedef struct xref_t
{
   char *mode;
   int mmal_mode;
} XREF_T;


/// Structure to cross reference exposure strings against the MMAL parameter equivalent
static XREF_T  exposure_map[] =
{
   {"auto",          MMAL_PARAM_EXPOSUREMODE_AUTO},
   {"night",         MMAL_PARAM_EXPOSUREMODE_NIGHT},
   {"nightpreview",  MMAL_PARAM_EXPOSUREMODE_NIGHTPREVIEW},
   {"backlight",     MMAL_PARAM_EXPOSUREMODE_BACKLIGHT},
   {"spotlight",     MMAL_PARAM_EXPOSUREMODE_SPOTLIGHT},
   {"sports",        MMAL_PARAM_EXPOSUREMODE_SPORTS},
   {"snow",          MMAL_PARAM_EXPOSUREMODE_SNOW},
   {"beach",         MMAL_PARAM_EXPOSUREMODE_BEACH},
   {"verylong",      MMAL_PARAM_EXPOSUREMODE_VERYLONG},
   {"fixedfps",      MMAL_PARAM_EXPOSUREMODE_FIXEDFPS},
   {"antishake",     MMAL_PARAM_EXPOSUREMODE_ANTISHAKE},
   {"fireworks",     MMAL_PARAM_EXPOSUREMODE_FIREWORKS}
};

static const int exposure_map_size = sizeof(exposure_map) / sizeof(exposure_map[0]);

/// Structure to cross reference awb strings against the MMAL parameter equivalent
static XREF_T awb_map[] =
{
   {"off",           MMAL_PARAM_AWBMODE_OFF},
   {"auto",          MMAL_PARAM_AWBMODE_AUTO},
   {"sun",           MMAL_PARAM_AWBMODE_SUNLIGHT},
   {"cloud",         MMAL_PARAM_AWBMODE_CLOUDY},
   {"shade",         MMAL_PARAM_AWBMODE_SHADE},
   {"tungsten",      MMAL_PARAM_AWBMODE_TUNGSTEN},
   {"fluorescent",   MMAL_PARAM_AWBMODE_FLUORESCENT},
   {"incandescent",  MMAL_PARAM_AWBMODE_INCANDESCENT},
   {"flash",         MMAL_PARAM_AWBMODE_FLASH},
   {"horizon",       MMAL_PARAM_AWBMODE_HORIZON}
};

static const int awb_map_size = sizeof(awb_map) / sizeof(awb_map[0]);


//////////////////////////////////////////// From RaspiCLI.c


/**
 * Function to take a string, a mapping, and return the int equivalent
 * @param str Incoming string to match
 * @param map Mapping data
 * @param num_refs The number of items in the mapping data
 * @return The integer match for the string, or -1 if no match
 */
int raspicli_map_xref(const char *str, const XREF_T *map, int num_refs)
{
   int i;

   for (i=0;i<num_refs;i++)
   {
      if (!strcasecmp(str, map[i].mode))
      {
         return map[i].mmal_mode;
      }
   }
   return -1;
}
////////////////////////////////////////////


/**
 * Convert string to the MMAL parameter for exposure mode
 * @param str Incoming string to match
 * @return MMAL parameter matching the string, or the AUTO option if no match found
 */
MMAL_PARAM_EXPOSUREMODE_T exposure_mode_from_string(const char *str)
{
   int i = raspicli_map_xref(str, exposure_map, exposure_map_size);
   return (MMAL_PARAM_EXPOSUREMODE_T)i;
   /*
   if( i != -1)
      return (MMAL_PARAM_EXPOSUREMODE_T)i;

   vcos_log_error("Unknown exposure mode: %s", str);
   return MMAL_PARAM_EXPOSUREMODE_AUTO;
   */
}

/**
 * Convert string to the MMAL parameter for AWB mode
 * @param str Incoming string to match
 * @return MMAL parameter matching the string, or the AUTO option if no match found
 */
MMAL_PARAM_AWBMODE_T awb_mode_from_string(const char *str)
{
   int i = raspicli_map_xref(str, awb_map, awb_map_size);
   return (MMAL_PARAM_AWBMODE_T)i;
   /*
   if( i != -1)
      return (MMAL_PARAM_AWBMODE_T)i;

   vcos_log_error("Unknown awb mode: %s", str);
   return MMAL_PARAM_AWBMODE_AUTO;
   */
}


/**
 * Convert a MMAL status return value to a simple boolean of success
 * ALso displays a fault if code is not success
 *
 * @param status The error code to convert
 * @return 0 if status is sucess, 1 otherwise
 */
int mmal_status_to_int(MMAL_STATUS_T status)
{
   if (status == MMAL_SUCCESS)
      return 0;
   else
   {
      switch (status)
      {
      case MMAL_ENOMEM :   vcos_log_error("Out of memory"); break;
      case MMAL_ENOSPC :   vcos_log_error("Out of resources (other than memory)"); break;
      case MMAL_EINVAL:    vcos_log_error("Argument is invalid"); break;
      case MMAL_ENOSYS :   vcos_log_error("Function not implemented"); break;
      case MMAL_ENOENT :   vcos_log_error("No such file or directory"); break;
      case MMAL_ENXIO :    vcos_log_error("No such device or address"); break;
      case MMAL_EIO :      vcos_log_error("I/O error"); break;
      case MMAL_ESPIPE :   vcos_log_error("Illegal seek"); break;
      case MMAL_ECORRUPT : vcos_log_error("Data is corrupt \attention FIXME: not POSIX"); break;
      case MMAL_ENOTREADY :vcos_log_error("Component is not ready \attention FIXME: not POSIX"); break;
      case MMAL_ECONFIG :  vcos_log_error("Component is not configured \attention FIXME: not POSIX"); break;
      case MMAL_EISCONN :  vcos_log_error("Port is already connected "); break;
      case MMAL_ENOTCONN : vcos_log_error("Port is disconnected"); break;
      case MMAL_EAGAIN :   vcos_log_error("Resource temporarily unavailable. Try again later"); break;
      case MMAL_EFAULT :   vcos_log_error("Bad address"); break;
      default :            vcos_log_error("Unknown status error"); break;
      }

      return 1;
   }
}

/**
 * Give the supplied parameter block a set of default values
 * @params Pointer to parameter block
 */
void raspicamcontrol_set_defaults(RASPICAM_CAMERA_PARAMETERS *params)
{
   vcos_assert(params);

   params->sharpness = 0;
   params->contrast = 0;
   params->brightness = 50;
   params->saturation = 0;
   params->ISO = 0;                    // 0 = auto
   params->videoStabilisation = 0;
   params->exposureCompensation = 0;
   params->exposureMode = MMAL_PARAM_EXPOSUREMODE_AUTO;
   params->exposureMeterMode = MMAL_PARAM_EXPOSUREMETERINGMODE_AVERAGE;
   params->awbMode = MMAL_PARAM_AWBMODE_AUTO;
   params->imageEffect = MMAL_PARAM_IMAGEFX_NONE;
   params->colourEffects.enable = 0;
   params->colourEffects.u = 128;
   params->colourEffects.v = 128;
   params->rotation = 0;
   params->hflip = params->vflip = 0;
   params->roi.x = params->roi.y = 0.0;
   params->roi.w = params->roi.h = 1.0;
   params->shutter_speed = 0;          // 0 = auto
   params->awb_gains_r = 0;      // Only have any function if AWB OFF is used.
   params->awb_gains_b = 0;
   params->drc_level = MMAL_PARAMETER_DRC_STRENGTH_OFF;
   params->stats_pass = MMAL_FALSE;
   params->enable_annotate = 0;
   params->annotate_string[0] = '\0';
   params->annotate_text_size = 0;	//Use firmware default
   params->annotate_text_colour = -1;   //Use firmware default
   params->annotate_bg_colour = -1;     //Use firmware default
   params->stereo_mode.mode = MMAL_STEREOSCOPIC_MODE_NONE;
   params->stereo_mode.decimate = MMAL_FALSE;
   params->stereo_mode.swap_eyes = MMAL_FALSE;
}

/**
 * Get all the current camera parameters from specified camera component
 * @param camera Pointer to camera component
 * @param params Pointer to parameter block to accept settings
 * @return 0 if successful, non-zero if unsuccessful
 */
int raspicamcontrol_get_all_parameters(MMAL_COMPONENT_T *camera, RASPICAM_CAMERA_PARAMETERS *params)
{
   vcos_assert(camera);
   vcos_assert(params);

   if (!camera || !params)
      return 1;

/* TODO : Write these get functions
   params->sharpness = raspicamcontrol_get_sharpness(camera);
   params->contrast = raspicamcontrol_get_contrast(camera);
   params->brightness = raspicamcontrol_get_brightness(camera);
   params->saturation = raspicamcontrol_get_saturation(camera);
   params->ISO = raspicamcontrol_get_ISO(camera);
   params->videoStabilisation = raspicamcontrol_get_video_stabilisation(camera);
   params->exposureCompensation = raspicamcontrol_get_exposure_compensation(camera);
   params->exposureMode = raspicamcontrol_get_exposure_mode(camera);
   params->awbMode = raspicamcontrol_get_awb_mode(camera);
   params->imageEffect = raspicamcontrol_get_image_effect(camera);
   params->colourEffects = raspicamcontrol_get_colour_effect(camera);
   params->thumbnailConfig = raspicamcontrol_get_thumbnail_config(camera);
*/
   return 0;
}

/**
 * Set the specified camera to all the specified settings
 * @param camera Pointer to camera component
 * @param params Pointer to parameter block containing parameters
 * @return 0 if successful, none-zero if unsuccessful.
 */
/*
int raspicamcontrol_set_all_parameters(MMAL_COMPONENT_T *camera, const RASPICAM_CAMERA_PARAMETERS *params)
{
   int result;

   result  = raspicamcontrol_set_saturation(camera, params->saturation);
   result += raspicamcontrol_set_sharpness(camera, params->sharpness);
   result += raspicamcontrol_set_contrast(camera, params->contrast);
   result += raspicamcontrol_set_brightness(camera, params->brightness);
   result += raspicamcontrol_set_ISO(camera, params->ISO);
   result += raspicamcontrol_set_video_stabilisation(camera, params->videoStabilisation);
   result += raspicamcontrol_set_exposure_compensation(camera, params->exposureCompensation);
   result += raspicamcontrol_set_exposure_mode(camera, params->exposureMode);
   result += raspicamcontrol_set_metering_mode(camera, params->exposureMeterMode);
   result += raspicamcontrol_set_awb_mode(camera, params->awbMode);
   result += raspicamcontrol_set_awb_gains(camera, params->awb_gains_r, params->awb_gains_b);
   //   result += raspicamcontrol_set_imageFX(camera, params->imageEffect);
   result += raspicamcontrol_set_colourFX(camera, &params->colourEffects);
   //result += raspicamcontrol_set_thumbnail_parameters(camera, &params->thumbnailConfig);  TODO Not working for some reason
   result += raspicamcontrol_set_rotation(camera, params->rotation);
   result += raspicamcontrol_set_flips(camera, params->hflip, params->vflip);
   result += raspicamcontrol_set_ROI(camera, params->roi);
   result += raspicamcontrol_set_shutter_speed(camera, params->shutter_speed);
   //   result += raspicamcontrol_set_DRC(camera, params->drc_level);
   result += raspicamcontrol_set_stats_pass(camera, params->stats_pass);
   result += raspicamcontrol_set_annotate(camera, params->enable_annotate, params->annotate_string,
                       params->annotate_text_size,
                       params->annotate_text_colour,
                       params->annotate_bg_colour);

   return result;
}
*/

/**
 * Adjust the saturation level for images
 * @param camera Pointer to camera component
 * @param saturation Value to adjust, -100 to 100
 * @return 0 if successful, non-zero if any parameters out of range
 */
int raspicamcontrol_set_saturation(MMAL_COMPONENT_T *camera, int saturation)
{
   int ret = 0;

   if (!camera)
      return 1;

   if (saturation >= -100 && saturation <= 100)
   {
      MMAL_RATIONAL_T value = {saturation, 100};
      ret = mmal_status_to_int(mmal_port_parameter_set_rational(camera->control, MMAL_PARAMETER_SATURATION, value));
   }
   else
   {
      vcos_log_error("Invalid saturation value");
      ret = 1;
   }

   return ret;
}

/**
 * Set the sharpness of the image
 * @param camera Pointer to camera component
 * @param sharpness Sharpness adjustment -100 to 100
 */
int raspicamcontrol_set_sharpness(MMAL_COMPONENT_T *camera, int sharpness)
{
   int ret = 0;

   if (!camera)
      return 1;

   if (sharpness >= -100 && sharpness <= 100)
   {
      MMAL_RATIONAL_T value = {sharpness, 100};
      ret = mmal_status_to_int(mmal_port_parameter_set_rational(camera->control, MMAL_PARAMETER_SHARPNESS, value));
   }
   else
   {
      vcos_log_error("Invalid sharpness value");
      ret = 1;
   }

   return ret;
}

/**
 * Set the contrast adjustment for the image
 * @param camera Pointer to camera component
 * @param contrast Contrast adjustment -100 to  100
 * @return
 */
int raspicamcontrol_set_contrast(MMAL_COMPONENT_T *camera, int contrast)
{
   int ret = 0;

   if (!camera)
      return 1;

   if (contrast >= -100 && contrast <= 100)
   {
      MMAL_RATIONAL_T value = {contrast, 100};
      ret = mmal_status_to_int(mmal_port_parameter_set_rational(camera->control, MMAL_PARAMETER_CONTRAST, value));
   }
   else
   {
      vcos_log_error("Invalid contrast value");
      ret = 1;
   }

   return ret;
}

/**
 * Adjust the brightness level for images
 * @param camera Pointer to camera component
 * @param brightness Value to adjust, 0 to 100
 * @return 0 if successful, non-zero if any parameters out of range
 */
int raspicamcontrol_set_brightness(MMAL_COMPONENT_T *camera, int brightness)
{
   int ret = 0;

   if (!camera)
      return 1;

   if (brightness >= 0 && brightness <= 100)
   {
      MMAL_RATIONAL_T value = {brightness, 100};
      ret = mmal_status_to_int(mmal_port_parameter_set_rational(camera->control, MMAL_PARAMETER_BRIGHTNESS, value));
   }
   else
   {
      vcos_log_error("Invalid brightness value");
      ret = 1;
   }

   return ret;
}

/**
 * Adjust the ISO used for images
 * @param camera Pointer to camera component
 * @param ISO Value to set TODO :
 * @return 0 if successful, non-zero if any parameters out of range
 */
int raspicamcontrol_set_ISO(MMAL_COMPONENT_T *camera, int ISO)
{
   if (!camera)
      return 1;

   return mmal_status_to_int(mmal_port_parameter_set_uint32(camera->control, MMAL_PARAMETER_ISO, ISO));
}

/**
 * Adjust the metering mode for images
 * @param camera Pointer to camera component
 * @param saturation Value from following
 *   - MMAL_PARAM_EXPOSUREMETERINGMODE_AVERAGE,
 *   - MMAL_PARAM_EXPOSUREMETERINGMODE_SPOT,
 *   - MMAL_PARAM_EXPOSUREMETERINGMODE_BACKLIT,
 *   - MMAL_PARAM_EXPOSUREMETERINGMODE_MATRIX
 * @return 0 if successful, non-zero if any parameters out of range
 */
int raspicamcontrol_set_metering_mode(MMAL_COMPONENT_T *camera, MMAL_PARAM_EXPOSUREMETERINGMODE_T m_mode )
{
   MMAL_PARAMETER_EXPOSUREMETERINGMODE_T meter_mode = {{MMAL_PARAMETER_EXP_METERING_MODE,sizeof(meter_mode)},
                                                      m_mode};
   if (!camera)
      return 1;

   return mmal_status_to_int(mmal_port_parameter_set(camera->control, &meter_mode.hdr));
}


/**
 * Set the video stabilisation flag. Only used in video mode
 * @param camera Pointer to camera component
 * @param saturation Flag 0 off 1 on
 * @return 0 if successful, non-zero if any parameters out of range
 */
int raspicamcontrol_set_video_stabilisation(MMAL_COMPONENT_T *camera, int vstabilisation)
{
   if (!camera)
      return 1;

   return mmal_status_to_int(mmal_port_parameter_set_boolean(camera->control, MMAL_PARAMETER_VIDEO_STABILISATION, vstabilisation));
}

/**
 * Adjust the exposure compensation for images (EV)
 * @param camera Pointer to camera component
 * @param exp_comp Value to adjust, -10 to +10
 * @return 0 if successful, non-zero if any parameters out of range
 */
int raspicamcontrol_set_exposure_compensation(MMAL_COMPONENT_T *camera, int exp_comp)
{
   if (!camera)
      return 1;

   return mmal_status_to_int(mmal_port_parameter_set_int32(camera->control, MMAL_PARAMETER_EXPOSURE_COMP , exp_comp));
}


/**
 * Set exposure mode for images
 * @param camera Pointer to camera component
 * @param mode Exposure mode to set from
 *   - MMAL_PARAM_EXPOSUREMODE_OFF,
 *   - MMAL_PARAM_EXPOSUREMODE_AUTO,
 *   - MMAL_PARAM_EXPOSUREMODE_NIGHT,
 *   - MMAL_PARAM_EXPOSUREMODE_NIGHTPREVIEW,
 *   - MMAL_PARAM_EXPOSUREMODE_BACKLIGHT,
 *   - MMAL_PARAM_EXPOSUREMODE_SPOTLIGHT,
 *   - MMAL_PARAM_EXPOSUREMODE_SPORTS,
 *   - MMAL_PARAM_EXPOSUREMODE_SNOW,
 *   - MMAL_PARAM_EXPOSUREMODE_BEACH,
 *   - MMAL_PARAM_EXPOSUREMODE_VERYLONG,
 *   - MMAL_PARAM_EXPOSUREMODE_FIXEDFPS,
 *   - MMAL_PARAM_EXPOSUREMODE_ANTISHAKE,
 *   - MMAL_PARAM_EXPOSUREMODE_FIREWORKS,
 *
 * @return 0 if successful, non-zero if any parameters out of range
 */
int raspicamcontrol_set_exposure_mode(MMAL_COMPONENT_T *camera, MMAL_PARAM_EXPOSUREMODE_T mode)
{
   MMAL_PARAMETER_EXPOSUREMODE_T exp_mode = {{MMAL_PARAMETER_EXPOSURE_MODE,sizeof(exp_mode)}, mode};

   if (!camera)
      return 1;

   return mmal_status_to_int(mmal_port_parameter_set(camera->control, &exp_mode.hdr));
}


/**
 * Set the aWB (auto white balance) mode for images
 * @param camera Pointer to camera component
 * @param awb_mode Value to set from
 *   - MMAL_PARAM_AWBMODE_OFF,
 *   - MMAL_PARAM_AWBMODE_AUTO,
 *   - MMAL_PARAM_AWBMODE_SUNLIGHT,
 *   - MMAL_PARAM_AWBMODE_CLOUDY,
 *   - MMAL_PARAM_AWBMODE_SHADE,
 *   - MMAL_PARAM_AWBMODE_TUNGSTEN,
 *   - MMAL_PARAM_AWBMODE_FLUORESCENT,
 *   - MMAL_PARAM_AWBMODE_INCANDESCENT,
 *   - MMAL_PARAM_AWBMODE_FLASH,
 *   - MMAL_PARAM_AWBMODE_HORIZON,
 * @return 0 if successful, non-zero if any parameters out of range
 */
int raspicamcontrol_set_awb_mode(MMAL_COMPONENT_T *camera, MMAL_PARAM_AWBMODE_T awb_mode)
{
   MMAL_PARAMETER_AWBMODE_T param = {{MMAL_PARAMETER_AWB_MODE,sizeof(param)}, awb_mode};

   if (!camera)
      return 1;

   return mmal_status_to_int(mmal_port_parameter_set(camera->control, &param.hdr));
}

int raspicamcontrol_set_awb_gains(MMAL_COMPONENT_T *camera, float r_gain, float b_gain)
{
   MMAL_PARAMETER_AWB_GAINS_T param = {{MMAL_PARAMETER_CUSTOM_AWB_GAINS,sizeof(param)}, {0,0}, {0,0}};

   if (!camera)
      return 1;

   if (!r_gain || !b_gain)
      return 0;

   param.r_gain.num = (unsigned int)(r_gain * 65536);
   param.b_gain.num = (unsigned int)(b_gain * 65536);
   param.r_gain.den = param.b_gain.den = 65536;
   return mmal_status_to_int(mmal_port_parameter_set(camera->control, &param.hdr));
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

/**
 * Set the flips state of the image
 * @param camera Pointer to camera component
 * @param hflip If true, horizontally flip the image
 * @param vflip If true, vertically flip the image
 *
 * @return 0 if successful, non-zero if any parameters out of range
 */
int raspicamcontrol_set_flips(MMAL_COMPONENT_T *camera, int hflip, int vflip)
{
   MMAL_PARAMETER_MIRROR_T mirror = {{MMAL_PARAMETER_MIRROR, sizeof(MMAL_PARAMETER_MIRROR_T)}, MMAL_PARAM_MIRROR_NONE};

   if (hflip && vflip)
      mirror.value = MMAL_PARAM_MIRROR_BOTH;
   else
   if (hflip)
      mirror.value = MMAL_PARAM_MIRROR_HORIZONTAL;
   else
   if (vflip)
      mirror.value = MMAL_PARAM_MIRROR_VERTICAL;

   mmal_port_parameter_set(camera->output[0], &mirror.hdr);
   mmal_port_parameter_set(camera->output[1], &mirror.hdr);
   return mmal_port_parameter_set(camera->output[2], &mirror.hdr);
}

/**
 * Set the ROI of the sensor to use for captures/preview
 * @param camera Pointer to camera component
 * @param rect   Normalised coordinates of ROI rectangle
 *
 * @return 0 if successful, non-zero if any parameters out of range
 */
int raspicamcontrol_set_ROI(MMAL_COMPONENT_T *camera, PARAM_FLOAT_RECT_T rect)
{
   MMAL_PARAMETER_INPUT_CROP_T crop = {{MMAL_PARAMETER_INPUT_CROP, sizeof(MMAL_PARAMETER_INPUT_CROP_T)}};

   crop.rect.x = (65536 * rect.x);
   crop.rect.y = (65536 * rect.y);
   crop.rect.width = (65536 * rect.w);
   crop.rect.height = (65536 * rect.h);

   return mmal_port_parameter_set(camera->control, &crop.hdr);
}

/**
 * Adjust the exposure time used for images
 * @param camera Pointer to camera component
 * @param shutter speed in microseconds
 * @return 0 if successful, non-zero if any parameters out of range
 */
int raspicamcontrol_set_shutter_speed(MMAL_COMPONENT_T *camera, int speed)
{
   if (!camera)
      return 1;

   return mmal_status_to_int(mmal_port_parameter_set_uint32(camera->control, MMAL_PARAMETER_SHUTTER_SPEED, speed));
}

int raspicamcontrol_set_stats_pass(MMAL_COMPONENT_T *camera, int stats_pass)
{
   if (!camera)
      return 1;

   return mmal_status_to_int(mmal_port_parameter_set_boolean(camera->control, MMAL_PARAMETER_CAPTURE_STATS_PASS, stats_pass));
}



/**
 * Asked GPU how much memory it has allocated
 *
 * @return amount of memory in MB
 */
/*
static int raspicamcontrol_get_mem_gpu(void)
{
   char response[80] = "";
   int gpu_mem = 0;
   if (vc_gencmd(response, sizeof response, "get_mem gpu") == 0)
      vc_gencmd_number_property(response, "gpu", &gpu_mem);
   return gpu_mem;
}
*/
/**
 * Ask GPU about its camera abilities
 * @param supported None-zero if software supports the camera 
 * @param detected  None-zero if a camera has been detected
 */
 /*
static void raspicamcontrol_get_camera(int *supported, int *detected)
{
   char response[80] = "";
   if (vc_gencmd(response, sizeof response, "get_camera") == 0)
   {
      if (supported)
         vc_gencmd_number_property(response, "supported", supported);
      if (detected)
         vc_gencmd_number_property(response, "detected", detected);
   }
}
 */

/**
 * Check to see if camera is supported, and we have allocated enough meooryAsk GPU about its camera abilities
 * @param supported None-zero if software supports the camera 
 * @param detected  None-zero if a camera has been detected
 */
  /*
void raspicamcontrol_check_configuration(int min_gpu_mem)
{
   int gpu_mem = raspicamcontrol_get_mem_gpu();
   int supported = 0, detected = 0;
   raspicamcontrol_get_camera(&supported, &detected);
   if (!supported)
      vcos_log_error("Camera is not enabled in this build. Try running \"sudo raspi-config\" and ensure that \"camera\" has been enabled\n");
   else if (gpu_mem < min_gpu_mem)
      vcos_log_error("Only %dM of gpu_mem is configured. Try running \"sudo raspi-config\" and ensure that \"memory_split\" has a value of %d or greater\n", gpu_mem, min_gpu_mem);
   else if (!detected)
      vcos_log_error("Camera is not detected. Please check carefully the camera module is installed correctly\n");
   else
      vcos_log_error("Failed to run camera app. Please check for firmware updates\n");
}

  */
