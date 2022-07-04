import paramiko
import time
import re
import os
from datetime import datetime
from typing import List, Tuple


class Commands:
    def __init__(
        self,
        boundary_pattern: str = '',
    ) -> None:

        self.boundary_pattern = boundary_pattern
        self.commands: List[str] = []

class SSHNetworkDeviceError(Exception):

    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class SSHNetworkDevice:
    """Common abstraction of connecting to the network devices by SSH.
    
    This class defined a bunch of methods that can be used to connect network devices,
    and execute single or multiple commands. Some of these methods are empty and you need to re-write them.

    Attributes:
        debug: A flag for `_print_debug_data`.
        deep_debug: A flag for `_print_deep_debug_data`.

    Args:
        host: The IP address or hostname of your device. When you provide the hostname, typically you need to \
            provide the domain name like router.example.com.
        username: Your account that is used to operate the network device.
        password: Password of your account.
        domain_suffix: When you login into the device using the IP address directly, you may not need to set this \
            attribute.
        privilege_password: If your account hasn't privilege permission, you need to provide the password to \
            enter the privilege mode.
        default_boundary_pattern: You can re-write `_set_default_boundary_pattern` to address this attribute.
        initial_command: You can re-write `_set_initial_command` to address this attribute.
    """
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        domain_suffix: str = '',
        privilege_password: str = None,
        debug: bool = False,
        deep_debug: bool = False,
        default_boundary_pattern='',
        initial_command=''
    ) -> None:

        self._host = host
        self._domain_suffix = domain_suffix
        self._privilege_password = privilege_password
        self.debug = debug
        self.deep_debug = deep_debug

        self._set_initial_command(initial_command=initial_command)
        self._set_default_boundary_pattern(pattern=default_boundary_pattern)
        self._set_prompt_vaule()

        # Initialize pramiko SSHClient and get a channel.
        # _client: A instance of paramino SSHClient.
        # _channel: It was from the client.invoke_shell().
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(
            paramiko.client.AutoAddPolicy())
        self._client.connect(
            hostname=self._host + self._domain_suffix,
            port=22,
            username=username,
            password=password,
            look_for_keys=False,
            allow_agent=False
        )
        self._channel = self._client.invoke_shell()

        # Initialize CLI flags for different modes.
        # _user_mode: Typically, when you at this mode, you can only get limited information about your device.
        # _privilege_mode: When you at this mode, you can get almost all the information about your device.
        # _config_mode: Before executing configuring task, you need to enter the config mode of your device.
        self._user_mode = False
        self._privilege_mode = False
        self._config_mode = False
        self._initial_actions()

    def _set_initial_command(self, initial_command: str):
        if initial_command:
            self._initial_command = initial_command
        else:
            self._initial_command = '\n'

    def _set_default_boundary_pattern(self, pattern: str) -> None:
        '''
        I am not sure if all network devices will include the hostname in the CLI prompt.
        So I don't let the host as the default value of boundary_pattern.
        You can re-write this method to change the logic of set the boundary_pattern.
        Here is an example, for Cisco platform——
        
        When you give a default_boundary_pattern arg when you instantiate an object,
        its _default_boundary_pattern attribute will equal the given arg, or it will equal 
        the hostname, like below shows:

        ```python3
        if pattern:
            self._default_boundary_pattern = pattern
        else:
            self._default_boundary_pattern = self._host
        ```
        '''
        self._default_boundary_pattern = pattern

    def _set_prompt_vaule(self) -> None:
        """
        You need to re-write these CLI prompts for specific network devcie platform/OS
        For example, for most Cisco platform——

            _user_mode_prompt = '>'

            _privilege_mode_prompt = '#'

            _config_mode_prompt = '(config.*)#'
            
        """
        self._user_mode_prompt = ''
        self._privilege_mode_prompt = ''
        self._config_mode_prompt = ''

    def _initial_actions(self) -> None:
        # CLEAR FIRST FEW ROWS
        clear_first_few_rows, _ = self._boundary_for_interactive(
            boundary_pattern=self._default_boundary_pattern)
        self._print_debug_data(
            debug_title=' CLEAR FIRST FEW ROWS ',
            echo_data=clear_first_few_rows
        )
        self._check_initial_mode()

    def _check_initial_mode(self) -> None:
        """
        An abstraction for initial mode checking after you login into the network device.
        You need to re-write this method to judge what mode you and set the pre-difined CLI flag.
            self.user_mode
            self.privilege_mode
            self.config_mode
        High-level methods exec_command and exec_multiple_commands will judge these flags.
        Once the expected flag is False, will try to enter the corresponding mode and set the flag.
        And after trying one time, if the flag is still False, will raise an exception.
        """
        raise SSHNetworkDeviceError(
            'Please don\'t use this class directly. You should create a sub-class for your network device.'
        )
        ...

    def _enter_privilege_mode(self) -> None: 
        """
        A method that is used to enter privilege mode on the network device.
        Privilege mode means you can execute almost any commands on the network device.
        And you can also enter the config mode from privilege mode to configure something.
        """
        raise SSHNetworkDeviceError(
            'Please don\'t use this class directly. You should create a sub-class for your network device.'
        )
        ...

    def _enter_config_mode(self) -> None: 
        """
        A method that is used to enter config mode on the network device.
        Config mode means you can configure something there.
        """
        raise SSHNetworkDeviceError(
            'Please don\'t use this class directly. You should create a sub-class for your network device.'
        )
        ...

    def close(self) -> None:
        self._channel.close()
        self._client.close()

    def _flush_buffer(self, expired_time: int) -> str:
        """Take out data from the buffer.

        A common method only used in the class internal.
        Once data in the buffer is ready, it will take out and return it.

        Args:
            expired_time: After this time and still doesn't get any data, raise an exception.
        
        Returns:
            Return the decoded data from buffer.
        
        Raises:
            TimeoutError: Occured an error when the time over the expired_time and doesn't get any data
        """
        now = datetime.now().timestamp()
        while not self._channel.recv_ready():
            time.sleep(0.1)
            # When the time took over the expired_time, raise an exception.
            after_while = datetime.now().timestamp()
            print(after_while)
            if after_while - now >= expired_time:
                raise TimeoutError(
                    'It takes too long to get data from the remote device.')
            else:
                ...

        data = self._channel.recv(1000).decode('utf-8')
        return data

    def _boundary_for_interactive(self, boundary_pattern: str, expired_time: int = 30) -> Tuple[str, List[str]]:
        """Working above the `_flush_buffer` to get all data based on the boundary pattern.
        
        A common method only used in the class internal.

        Args:
            boundary_pattern: Used to check if all data has been recevied from the buffer.
            expired_time: As a parameter passed to the `_flush_buffer` method. After this time and still doesn't get any \
                data, raise an exception. The default value is 30.
        
        Returns:
            Return a tuple that include the raw data and splited raw data based on `\\n`
        """
        target_string = ''
        data = ''
        while re.match(boundary_pattern, target_string, re.IGNORECASE) is None:
            time.sleep(0.1)
            data += self._flush_buffer(expired_time=expired_time)

            self._print_deep_debug_data(
                debug_title=' BOUNDARY_FOR_INTERACTIVE IS WORKING: LOOP TO GET DATA ',
                echo_data=data
            )

            data_split = data.split('\n')

            self._print_deep_debug_data(
                debug_title=' BOUNDARY_FOR_INTERACTIVE IS WORKING: DATA_SPLIT ',
                echo_data=data_split
            )

            target_string = data_split[-1].lstrip(
                '\r').lstrip('\n').rstrip('\r').rstrip('\n')

            self._print_deep_debug_data(
                debug_title=' BOUNDARY_FOR_INTERACTIVE IS WORKING: RE.MATCH TARGET STRING ',
                echo_data=target_string
            )

        return data, data_split

    def _send(self, command: str = '', boundary_pattern: str = '') -> Tuple[str, List[str]]:
        """An low-level used for the `exec_command` and `exec_multiple_commands` method.

        A common method only used in the class internal.

        Args: 
            command: The command you want send to the network device
            boundary_pattern: The default value is ''. If you provide this arg, then it will use the boundary_pattern \
                that you provided directly. Or it will combine the _default_boundary_pattern and prompt based on the \
                    CLI mode.
        
        Returns:
            A list is split from the raw rows based on the `\\n` character.

        Raises:
            SSHNetworkDeviceError: An exception occurred when any of the CLI modes can't match.
        """

        if boundary_pattern:
            ...
        else:
            if self._user_mode:
                boundary_pattern = self._default_boundary_pattern + self._user_mode_prompt
            elif self._privilege_mode:
                boundary_pattern = self._default_boundary_pattern + self._privilege_mode_prompt
            elif self._config_mode:
                boundary_pattern = self._default_boundary_pattern + self._config_mode_prompt
            else:
                raise SSHNetworkDeviceError(
                    'Set boundary_pattern failed. Unexpected status.\nUser mode: {}\nPrivilege mode: {}\nConfig mode: {}'.format(
                        self._user_mode, self._privilege_mode, self._config_mode
                    )
                )

        if command == '\n':
            self._channel.send(command)
            command_debug_str = '\\n'
            print('COMMAND_DEBUG_STR: ', command_debug_str)
        else:
            self._channel.send(command + '\n')
            command_debug_str = command

        raw_rows, split_rows = self._boundary_for_interactive(
            boundary_pattern=boundary_pattern)

        self._print_debug_data(
            debug_title=' ISSUE COMMAND: \'%s\' ' % command_debug_str,
            echo_data=raw_rows
        )

        return raw_rows, split_rows

    def exec_command(self, command: Commands) -> List[str]:
        """A high-level api is used to execute one command on the network device.

        When you only want to execute one command you can use this method.
        You can set specific boundary_pattern to override the default_boundary_pattern.

        Args:
            command: A Commands object. You can set its boundary_pattern attribute to override the default_boundary_pattern. \
                The command.commands should only include one item, or it will raise a ValueError.
        
        Returns:
            A list is split from the raw rows based on the `\\n` character.
        
        Raises:
            ValueError: Occurred when the length of command.commands is not 1.
            SSHNetworkDeviceError: Occurred when privilege_mode is False.
        """

        if len(command.commands) == 1:
            _command = command.commands[0]
        else:
            raise ValueError(
                'The exec_command only use to execute one command. If you want to execute more commands, \
                    please use the exec_multiple_commands method.'
            )

        if not self._privilege_mode:
            self._enter_privilege_mode()
        else:
            ...

        if self._privilege_mode:
            _, split_rows = self._send(command=_command, boundary_pattern=command.boundary_pattern)
        else:
            raise SSHNetworkDeviceError(
                'You are not at the privilege mode. Currently you can only executing single command under the privilege mode.\n'
            )
        
        return split_rows

    def exec_multiple_commands(self, commands: Commands, config: bool = False) -> List[List[str]]:
        """A high-level api is used to execute multiple commands on the network device.

        This method will loop to execute the item in the commands and combine the data into one list and return.
        You can set specific boundary_pattern to override the default_boundary_pattern.

        Args:
            command: A Commands object. You can set its boundary_pattern attribute to override the default_boundary_pattern. \
                If the command.commands is empty, it will raise a ValueError.
            config: A flag should be set when you want to send commands for the config tasks.
        
        Returns:
            A list that includes multiple lists to contain data for every command.

        Raises:
            ValueError: Occurred when command.commands is empty.
            SSHNetworkDeviceError: Occurred when privilege_mode or config_mode is False.
        """
        if config:
            if not self._config_mode:
                self._enter_config_mode()
            else:
                ...
        else:
            if not self._privilege_mode:
                self._enter_privilege_mode()
            else:
                ...

        _result: List[List[str]] = []
        if self._privilege_mode or self._config_mode:
            if len(commands.commands) > 0:
                for command in commands.commands:
                    # print(command)
                    _, split_rows = self._send(command=command, boundary_pattern=commands.boundary_pattern)
                    _result.append(split_rows)
            else:
                raise ValueError(
                    'You didn\'t provide any command. The Commands.commands you provided is empty.'
                )
        else:
            raise SSHNetworkDeviceError(
                'You are not at the config or privilege mode. Currently you can only executing multiple commands under the privilege or config mode.\n'
            )
        
        return _result

    def _print_debug_data(self, debug_title: str, echo_data: str) -> None:
        if self.debug:
            self._print_debug_data_base(
                debug_title=debug_title, echo_data=echo_data, print_style='-')
        else:
            ...

    def _print_deep_debug_data(self, debug_title: str, echo_data: str) -> None:
        if self.deep_debug:
            self._print_debug_data_base(
                debug_title=debug_title, echo_data=echo_data, print_style='#')
        else:
            ...

    def _print_debug_data_base(self, debug_title: str, echo_data: str | list, print_style: str) -> None:
        terminal_columns_size = os.get_terminal_size().columns
        debug_frame = print_style * terminal_columns_size

        frame_prefix_suffix_len = int(
            (len(debug_frame) - len(debug_title))/2)
        print(debug_frame)
        print(' ' * frame_prefix_suffix_len +
              debug_title + ' ' * frame_prefix_suffix_len)
        print(debug_frame)

        print(echo_data)

        frame_prefix_suffix_len = int(
            (len(debug_frame) - len(' DEBUG INFO END '))/2)
        print(debug_frame)
        print(' ' * frame_prefix_suffix_len +
              ' DEBUG INFO END ' + ' ' * frame_prefix_suffix_len)
        print(debug_frame + '\n\n')
