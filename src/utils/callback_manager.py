from typing import Dict, Type, Callable, Any
import inspect
import logging
import asyncio

class CallbackManager:
    """
    Manages callbacks for different event types, allowing registration and triggering of functions.
    """
    def __init__(self):
        """
        Initializes the CallbackManager with empty dictionaries for callbacks and signatures.
        """
        self.callbacks = {}
        self.__callback_signatures = {}
    
    def list_callbacks(self):
        """
        Returns a list of all registered event type labels.

        Returns:
            List[str]: A list of event type labels.
        """
        return list(self.callbacks.keys())
    
    def define_callback(self, event_type_label: str, msg_signature: inspect.Signature):
        """
        Defines a new callback event type with a specified message signature.

        Args:
            event_type_label (str): The label for the event type.
            msg_signature (inspect.Signature): The signature of the messages that will be passed to the callbacks.

        Raises:
            Exception: If a callback with the same label already exists.
        """
        if event_type_label in self.callbacks:
            raise Exception(f"Callback <{event_type_label}> already exists in callback manager")
        self.callbacks[event_type_label] = []
        self.__callback_signatures[event_type_label] = msg_signature
        logging.debug(f"Defined callback <{event_type_label}>")

    def register_callback_executable(self, event_type_label: str, executable: Callable):
        """
        Registers a callable function as a callback for a specific event type.

        Args:
            event_type_label (str): The label for the event type.
            executable (Callable): The callable function to register as a callback.

        Raises:
            Exception: If the event type does not exist or if the callback signature does not match.
        """
        if event_type_label not in self.callbacks:
            raise Exception(f"Callback <{event_type_label}> does not exist in callback manager")
        signature = inspect.signature(executable)
        callback_sig = self.__callback_signatures.get(event_type_label)

        if callback_sig is None:
            raise Exception(f"Signature for <{event_type_label}> not defined")

        try:
            callback_sig.bind(*signature.parameters.values())
        except TypeError as e:
            raise Exception(f"Callback signature does not match: {e}")

        self.callbacks[event_type_label].append(executable)
        logging.debug(f"Callback <{event_type_label}> registered successfully.")

    async def trigger_callbacks(self, event_type_label: str, *args: Any, **kwargs: Any):
        """
        Triggers all registered callbacks for a specific event type.

        Args:
            event_type_label (str): The label for the event type.
            *args: Positional arguments to pass to the callbacks.
            **kwargs: Keyword arguments to pass to the callbacks.
        """
        if event_type_label in self.callbacks:
            tasks = []
            for callback in self.callbacks[event_type_label]:
                tasks.append(asyncio.create_task(callback(*args, **kwargs)))
            await asyncio.gather(*tasks)
        else:
            print(f"No callbacks registered for <{event_type_label}>")