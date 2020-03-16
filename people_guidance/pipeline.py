import multiprocessing as mp
import time
import logging
import pathlib
import datetime
from typing import Callable, Optional, List, Dict
from psutil import cpu_percent, virtual_memory

from .utils import get_logger, ROOT_LOG_DIR, init_logging
from .modules import Module


class Pipeline:

    def __init__(self, args=None):
        self.log_dir: pathlib.Path = self.create_log_dir()
        self.logger: logging.Logger = get_logger("pipeline", self.log_dir)
        self.modules: Dict[Module] = {}
        self.processes: List[mp.Process] = []
        self.args = args

    def start(self):
        self.connect_modules()
        with self:
            for module in self.modules.values():
                p = mp.Process(target=self.start_module, kwargs={"module": module}, daemon=True)
                self.processes.append(p)
                p.start()

            while True:
                time.sleep(3)
                if not all([proc.is_alive() for proc in self.processes]):
                    self.logger.exception("Found dead child process. Pipeline will terminate all children and exit.")
                    exit()
                else:
                    self.logger.info(f"Pipeline alive: CPU: {cpu_percent()}, Memory: {virtual_memory()._asdict()['percent']}")

    @staticmethod
    def start_module(module: Module):
        init_logging()
        with module:
            module.start()

    def add_module(self, constructor: Callable):
        module = constructor(log_dir=self.log_dir, args=self.args)
        if module.name in self.modules:
            raise RuntimeError(f"Could not create a module with name {module.name} "
                               "because another module had the same name. Module names must be unique!")
        self.modules.update({module.name: module})

    def connect_modules(self):
        for module in self.modules.values():
            try:
                for topic_name in module.input_topics:
                    topic = self.get_topic(topic_name)
                    module.subscribe(topic_name, topic)
            except KeyError:
                raise KeyError(f"Could not subscribe module {module.name}")

    def get_topic(self, topic_name):
        module_name, output_name = topic_name.split(":")
        if module_name not in self.modules:
            raise KeyError(
                f"Cannot subscribe to {topic_name}: Unknown module {module_name}. Must be one of {self.modules.keys()}")

        outputs = self.modules[module_name].outputs
        if output_name not in outputs:
            raise KeyError(f"Cannot subscribe to {topic_name}: Unknown output {output_name}. "
                           f"Must be one of {outputs.keys()}")
        return outputs[output_name]

    @staticmethod
    def create_log_dir() -> pathlib.Path:
        time_str = datetime.datetime.now().strftime("%Y-%m-%d__%H-%M-%S")
        log_dir = ROOT_LOG_DIR / time_str
        log_dir.mkdir(parents=True, exist_ok=False)
        return log_dir

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.warning("Terminating all children...")
        for proc in self.processes:
            proc.join(timeout=2)
            if proc.is_alive():
                self.logger.critical("Child did not exit fast enough and will be terminated.")
                proc.kill()



