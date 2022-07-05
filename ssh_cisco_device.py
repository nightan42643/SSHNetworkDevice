from ssh_network_device import *
from ipaddress import ip_address


def is_host_ip_address(host: str):
    try:
        host = ip_address(host)
        if host:
            return True
    except ValueError:
        return False

class SSHCiscoDevice(SSHNetworkDevice):

    def _set_default_boundary_pattern(self, pattern: str) -> None:
        if pattern:
            # Example: IOS-XR: 'rp.*\/rsp.*\/cpu.*router'
            self._default_boundary_pattern = pattern
        else:
            # Example: IOS | NX-OS: router
            self._default_boundary_pattern = self._host
            if is_host_ip_address(self._host):
                raise SSHNetworkDeviceError(
                    'The host you provided is an ip address. In this case, you should provide boundary_partten.'
                )
            else:
                ...

    def _set_prompt_vaule(self) -> None:
        self._user_mode_prompt = '>'
        self._privilege_mode_prompt = '#'
        self._config_mode_prompt = '(config.*)#'

    def _check_initial_mode(self) -> None:
        '''
        Send initial command and check current CLI mode, then set the corresponding CLI flag.
        '''

        # Here can't use the high-level API (exec_command and exec_multiple_command)
        # Because these high-level API need to check the CLI mode flag.
        # But at the initial stage, all CLI mode flags are False.
        _, initial_command_return_data_split = self._send(
            command=self._initial_command, boundary_pattern=self._default_boundary_pattern
        )

        target_string = initial_command_return_data_split[-1].lower()

        if re.search(self._default_boundary_pattern + self._user_mode_prompt, target_string, re.IGNORECASE) is not None:
            self._user_mode = True
            self._privilege_mode = False
            self._config_mode = False
        elif re.search(self._default_boundary_pattern + self._privilege_mode_prompt, target_string, re.IGNORECASE) is not None:
            self._user_mode = False
            self._privilege_mode = True
            self._config_mode = False
            self._terminal_length_zero()
        else:
            raise SSHNetworkDeviceError(
                'Unexpected CLI prompt: {}'.format(target_string)
            )

    def _terminal_length_zero(self) -> None:
        command = Commands()
        command.commands = ['terminal length 0']
        self.exec_command(command=command)

    def _enter_privilege_mode(self) -> None:
        '''
        NXOS doesn't support > prompt.
        It only has # promprt.
        '''
        if self._user_mode:
            if self._privilege_password is None:
                self._channel.close()
                raise SSHNetworkDeviceError(
                    'Missing Privilege Mode Password'
                )
            else:
                commands = Commands()
                commands.commands = [
                    'enable',
                    self._privilege_password
                ]
                commands.boundary_pattern = self._default_boundary_pattern + \
                    self._privilege_mode_prompt
                self.exec_multiple_commands(commands=commands)

                self._user_mode = False
                self._privilege_mode = True
                self._config_mode = False

                self._terminal_length_zero()
        else:
            raise SSHNetworkDeviceError(
                'Unexpected CLI mode flag.\nUser mode: {}\nPrivilege mode: {}\nConfig mode: {}'.format(
                    self._user_mode, self._privilege_mode, self._config_mode
                )
            )
