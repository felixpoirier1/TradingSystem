
from enum import Enum 
from collections import namedtuple

ArgTemplate = namedtuple('ArgTemplate', ['name_or_flags', 'type', 'required', 'default', 'choices', 'help'])

ARGUMENT_TEMPLATES = [
        ArgTemplate("--level", type=str, required=False, default= "INFO", choices=["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"], help="Set logging level"),
        ArgTemplate("--verbose", type=str, required=False, default= "true", choices=["true", "false"], help="Enable verbose logging"),
        ArgTemplate("--interactive", type=str, required=False, default= "true", choices=["true", "false"], help="Enable interactive mode"),
        ArgTemplate("--gw-config", type=str, required=False, default= ".config/gateway_params.yaml", choices=None, help="Path to gateway config file"),
        ArgTemplate("--client-config", type=str, required=False, default= ".config/client_params.yaml", choices=None, help="Path to client config file"),
        ArgTemplate("--log-config", type=str, required=False, default= ".config/logging_config.yaml", choices=None, help="Path to logging config file")
]