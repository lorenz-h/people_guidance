import multiprocessing as mp
import pathlib
import logging
import traceback
import queue
import time
import multiprocessing as mp

from typing import Optional, Any, Dict, List, Tuple, Callable, Union

from ..utils import get_logger


class ModuleService:
    def __init__(self, name: str):
        self.name = name
        self.requests = mp.Queue(maxsize=1)
        self.responses = mp.Queue(maxsize=1)
        self.handler = self.default_handler
        self.logger = None
        self.current_request = None

    def register_handler(self, handler: Callable):
        self.handler = handler

    def default_handler(self, request) -> Dict:
        self.logger.warning("Request made to service {self.name} which has no handler. Returning an arbitrary response.")
        return {"id": request["id"], "payload": None}


class Module:
    def __init__(self, name: str, log_dir: pathlib.Path, outputs: List[Tuple[str, int]] = None,
                 inputs: List[str] = None, services: List[str] = None, requests: List[str] = None):

        self.name: str = name
        self.log_dir: pathlib.Path = log_dir
        self.log_level = logging.DEBUG

        self.inputs: Dict[str, Optional[mp.Queue]] = {} if inputs is None else {channel: None for channel in inputs}
        self.outputs: Dict[str, mp.Queue] = {} if outputs is None else \
            {name: mp.Queue(maxsize=maxsize) for (name, maxsize) in outputs}

        self.requests: Dict[str, Dict[str, mp.Queue]] = {} if requests is None else \
            {channel: {"timeout": timeout} for channel, timeout in requests}
        self.services: Dict[str, ModuleService] = {} if services is None \
            else {name: ModuleService(name) for name in services}

    def subscribe(self, channel: str, queue_obj: mp.Queue):
        return self.inputs.update({channel: queue_obj})

    def add_request_target(self, request_channel, request_queue, response_queue):
        self.requests[request_channel].update({"requests": request_queue, "responses": response_queue})

    def publish(self, channel: str, data: Any, validity: int, timestamp=None) -> None:
        if timestamp is None:
            # We need to set the timestamp if not set explicitly
            timestamp = self.get_time_ms()

        while True:
            try:
                self.outputs[channel].put_nowait({'data': data, 'timestamp': timestamp, 'validity': validity})
                break
            except queue.Full:
                try:
                    self.outputs[channel].get_nowait()
                except queue.Empty:
                    pass

    def get(self, channel: str) -> Dict:
        # If the queue is empty we return an empty dict, error handling should be done after

        def is_valid(msg_body_item: Dict):
            return msg_body_item is not None and msg_body_item['timestamp'] + \
                   msg_body_item['validity'] < self.get_time_ms()

        try:
            msg_body = None
            while True:
                # get objects from the queue until it is either empty or a valid msg_body is found.
                # if the queue is empty queue.Empty will be raised.
                msg_body = self.inputs[channel].get_nowait()
                if is_valid(msg_body):
                    return msg_body
                elif msg_body is not None:
                    self.logger.info("found stale msg")
        except queue.Empty:
            return dict()

    def make_request(self, target_name, request_payload: Dict):
        full_exc = queue.Full(f"You made another request to {target_name} before it finished the first request."
                              f"You must use await_response to wait for the response first.")

        request_payload.update({"timeout": self.requests[target_name]["timeout"]})
        if not self.requests[target_name]["requests"].full():
            try:
                self.requests[target_name]["requests"].put_nowait(request_payload)
            except queue.Full:
                raise full_exc
        else:
            raise full_exc

    def await_response(self, target_name) -> Any:
        # this call blocks until a response is received.
        return self.requests[target_name]["responses"].get(timeout=self.requests[target_name]["timeout"])

    def handle_requests(self):
        for service_name in self.services:
            service = self.services[service_name]
            if service.current_request is not None:
                self.respond(service_name, service.current_request)
            elif not service.requests.empty():
                try:
                    request: Dict = service.requests.get_nowait()
                    self.respond(service_name, request)
                except queue.Empty:
                    pass

    def get_requests(self, service_name):

        service = self.services[service_name]
        if service.current_request is not None:
            self.respond(service_name, service.current_request)
        elif not service.requests.empty():
            try:
                request: Dict = service.requests.get_nowait()
                return request
            except queue.Empty:
                pass

        return None

    def respond(self, service_name: str, request: Dict):
        full_exc = queue.Full("Response was not read by requesting process. You must read the response in the "
                              "requesting process before making another request.")
        service = self.services[service_name]
        if not service.responses.full():
            try:
                handler_result = service.handler(request)
                if handler_result is not None:
                    response = {"id": request["id"], "payload": handler_result}
                    service.responses.put_nowait(response)
                    service.current_request = None
                else:
                    self.logger.debug(f"Service {service_name} was not yet ready to "
                                      f"respond to request {request['id']}.")
                    service.current_request = request
            except queue.Full:
                raise full_exc
        else:
            raise full_exc

    def start(self):
        raise NotImplementedError

    @staticmethod
    def get_time_ms():
        # https://www.python.org/dev/peps/pep-0418/#time-monotonic
        return int(round(time.monotonic() * 1000))

    def __enter__(self):
        self.logger: logging.Logger = get_logger(f"module_{self.name}", self.log_dir, level=self.log_level)
        for service in self.services.values():
            service.logger = self.logger.getChild(f"service_{service.name}")
        self.logger.info(f"Module {self.name} started.")

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.warning(f"Module {self.name} is shutting down...")
        self.cleanup()
        self.logger.exception(traceback.format_exc())
        exit()

    def cleanup(self):
        pass
