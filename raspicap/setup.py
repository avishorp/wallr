from distutils.core import setup, Extension

raspicap = Extension('raspicap',
                    define_macros = [('VERSION', '1')],
                    include_dirs = [
                      '/opt/vc/include',
                      '/opt/vc/include/interface/vcos/pthreads',
                      '/opt/vc/include/interface/vmcs_host',
                      '/opt/vc/include/interface/vmcs_host/linux'],

                    libraries = [
                      'mmal_core',
                      'mmal_util',
                      'mmal_vc_client',
                      'vcos',
                      'bcm_host',
                      'pthread'
                      ],
                    library_dirs = ['/opt/vc/lib'],
                    sources = ['RaspiCamControl.cpp', 'raspicap.cpp'
                               
                               ])

setup (name = 'raspicap',
       version = '1.0',
       description = 'MMAL Based Raspberry Pi Camera Interface',
       author = 'Avishay Orpaz',
       author_email = 'avishorp@gmail.com',
       url = 'https://docs.python.org/extending/building',
       ext_modules = [raspicap])
