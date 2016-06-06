import traceback
import sys

import subprocess

import config
from pipot.services import ServiceLoader, IService

services_to_enable = config.config_inst.get_services()

for service in services_to_enable:
    class_name = service['name']
    try:
        instance = ServiceLoader.get_class_instance(
            service['name'], None, service['config'])
        if isinstance(instance, IService.IService):
            print('Processing installation for %s' % service['name'])
            apt_deps = instance.get_apt_dependencies()
            if len(apt_deps) > 0:
                apt = ['apt-get', '-q', '-y', 'install']
                apt.extend(apt_deps)
                print('Calling %s' % " ".join(apt))
                # Call apt-get install
                _ph = subprocess.Popen(apt)
                _ph.wait()
            else:
                print('No apt dependencies for %s' % service['name'])

            pip_deps = instance.get_pip_dependencies()
            if len(pip_deps) > 0:
                pip = ['pip', 'install']
                pip.extend(pip_deps)
                print('Calling %s' % " ".join(pip))
                _ph = subprocess.Popen(pip)
                _ph.wait()
            else:
                print('No pip dependencies for %s' % service['name'])

            print('Running after_install_hook for %s: %s' % (
                service['name'],
                'success' if instance.after_install_hook() else 'failure'
                )
            )
        else:
            print('%s is not a IService; skipping')
    except Exception as e:
        print('Failed to load the %s service: %s' % (class_name,
                                                     traceback.format_exc()))
