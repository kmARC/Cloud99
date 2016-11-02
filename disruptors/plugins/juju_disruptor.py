from disruptors.baseDisruptor import BaseDisruptor
import ha_engine.ha_infra as infra
from ha_engine.ha_constants import HAConstants
from utils import utils
import time
import yaml

LOG = infra.ha_logging(__name__)


class JujuDisruptor(BaseDisruptor):

    report_headers = ['state', 'type', 'uptime']
    ha_report = []
    sync = None
    finish_execution = None

    def juju_disruption(self, sync=None, finish_execution=None):
        self.sync = sync
        self.finish_execution = finish_execution
        infra.display_on_terminal(self, "Entering  Juju Disruption plugin")

        table_name = "Juju Disruption"
        infra.create_report_table(self, table_name)
        infra.add_table_headers(self, table_name,
                                ["Host", "Juju Process",
                                 "Timestamp",
                                 "Status of Disruption"])
        input_args_dict = self.get_input_arguments()
        app_name = input_args_dict.keys()[0]
        input_args = input_args_dict.get(app_name, None)
        host_config = infra.get_openstack_config()

        if input_args:
            print "Inpt " + str(input_args)
            disruption_type = input_args.get('disruption', None)
        infra.display_on_terminal(self, "Juju ", app_name,
                                  " will be disrupted")

        nodes_to_be_disrupted = []
        juju = {}
        user = ''
        key_filename = ''
        password = ''
        timeout = 10
        for node in host_config:
            if 'filename' not in host_config[node]:
                # TODO: exception
                break

            with open(host_config[node].get('filename'), 'r') as stream:
                try:
                    juju = yaml.load(stream)
                except yaml.YAMLError as exc:
                    print(exc)
                    return
            break
        
            # get the username from config
            #
            if 'user' not in host_config[node]:
                user = 'ubuntu'
            else:
                user = host_config[node].get('user')
             
            # get the ssh keyfile name from config, if not set fallback to
            # password auth
            if 'key_filename' in host_config[node]:
                key_filename = host_config[node].get('key_filename')
            else:
                if 'password' not in host_config[node]:
                    password = ''
                else:
                    password = host_config[node].get('password')
                    
            # get the ssh timeout
            #
            if 'timeout' in host_config[node]:
                timeout = host_config[node].get('timeout')

        if app_name not in juju['applications']:
            # TODO: exception
            print("No " + app_name + " in juju config")
            return

        app = juju['applications'][app_name]
        if 'units' not in app:
            # TODO: exception
            print ("No units for " + app_name)
            return

        containers = []
        for unit_name, unit in app['units'].items():
            if 'lxd' not in unit["machine"]:
                # TODO: exception
                print ("Not containerized: " + app_name)
                return
            containers.append(unit['machine'])

        print("Containers to disrupt: ", containers)

        for machine_name, machine in juju['machines'].items():
            if 'containers' not in machine:
                continue
            for container_name, container in machine['containers'].items():
                if container_name in containers:
                    infra.display_on_terminal(self, machine['dns-name'], " will be disrupted ")
                    nodes_to_be_disrupted.append((machine['dns-name'], container['instance-id']))
                    break

        ha_start_delay = self.get_ha_start_delay()
        if sync:
            infra.display_on_terminal(self, "Waiting for notification")
            infra.wait_for_notification(sync)
            infra.display_on_terminal(self, "Received notification, Starting")
            # Start the actual disruption after 45 seconds
            time.sleep(ha_start_delay)

        ha_interval = self.get_ha_interval()
        disruption_count = self.get_disruption_count()
        if disruption_type == 'infinite':
            # Override the disruption count in executor.yaml
            disruption_count = 1
        while infra.is_execution_completed(self.finish_execution) is False:
            if disruption_count:
                disruption_count = disruption_count - 1
                for node, instance_id in nodes_to_be_disrupted:
                    container_stop_command = "lxc stop " + instance_id
                    container_start_command = "lxc start " + instance_id
                    ip = node
                    infra.display_on_terminal(self, "Stopping ", instance_id)
                    infra.display_on_terminal(self, "Executing `", container_stop_command, "` on ", ip)
                    # if a ssh keyfile is provided use it, othwise fall back to
                    # password auth
                    if length(key_filename) > 0:
                        infra.display_on_terminal(self, "Using ssh key authentication")
                        #code, out, err = infra.ssh_and_execute_command(
                        #    ip, user, None, container_stop_command, timeout, None, key_filename)
                    else:
                        infra.display_on_terminal(self, "Using ssh password authentication")
                        # code, out, error = infra.ssh_and_execute_command(
                        #         ip, user, password, container_stop_command)
                    infra.add_table_rows(self, table_name, [[ip,
                                                           instance_id,
                                                           utils.get_timestamp(),
                                                           HAConstants.WARNING +
                                                           'Stopped' +
                                                           HAConstants.ENDC]])
                    if disruption_type == 'infinite':
                        infra.display_on_terminal(self,"Infinite disruption chosen bring up container manually")
                        break
                    infra.display_on_terminal(self, "Sleeping for interval ",
                                        str(ha_interval), " seconds")
                    time.sleep(ha_interval)
                    infra.display_on_terminal(self, "Starting ", instance_id)
                    infra.display_on_terminal(self, "Executing ", container_start_command)
                    # if a ssh keyfile is provided use it, othwise fall back to
                    # password auth
                    if length(key_filename) > 0:
                        infra.display_on_terminal(self, "Using ssh key authentication")
                        #code, out, err = infra.ssh_and_execute_command(
                        #    ip, user, None, container_stop_command, timeout, None, key_filename)
                    else:
                        infra.display_on_terminal(self, "Using ssh password authentication")
                        # code, out, error = infra.ssh_and_execute_command(
                        #         ip, user, password, container_stop_command)

                    time.sleep(ha_interval)
                    infra.add_table_rows(self, table_name, [[ip,
                                                           instance_id,
                                                           utils.get_timestamp(),
                                                           HAConstants.OKGREEN +
                                                           'Started' +
                                                           HAConstants.ENDC]])

        # bring it back to stable state
        # if disruption_type != 'infinite':
            # infra.display_on_terminal(self, "Bringing the container to stable state")
            # infra.display_on_terminal(self, "Executing ", container_start_command)
            # code, out, error = infra.ssh_and_execute_command(ip, user, password,
                                                         # container_start_command)

        infra.display_on_terminal(self, "Finishing Juju Disruption")

    def set_expected_failures(self):
        pass

    def node_disruption(self, sync=None, finish_execution=None):
        pass

    def start_disruption(self, sync=None, finish_execution=None):
        pass

    def is_module_exeution_completed(self):
        return infra.is_execution_completed(finish_execution=
                                            self.finish_execution)

    def stop_disruption(self):
        pass

    def set_report(self):
        pass

    def display_report(self):
        pass

