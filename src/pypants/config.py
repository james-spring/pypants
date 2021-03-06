"""Contains a configuration parser and project config singleton"""
from configparser import ConfigParser
import json
from pathlib import Path
from typing import List, Optional, Set

from .util import get_git_top_level_path


class Config:
    """pypants configuration parser

    Configuration is based on a .pypants.cfg file.

    The schema for the file in the git project root is::

        [project]
        ignore_dirs = []
        ignore_targets = []
        python_package_name_prefix = ""
        third_party_import_map_path = "3rdparty/python/import-map.json"
        third_party_requirements_path = "3rdparty/python/requirements.txt"
        top_dirs = ["."]

    The schema for the file in an individual python package is::

        [package]
        extra_dependencies = ["lib/python_core/src", ...]
        extra_tags = ["my-tag", ...]
        generate_build_file = <bool>
        generate_local_binary = <bool>
        generate_pytest_binary = <bool>
        include_test_coverage = <bool>
        type = "library"|"binary"|...

    Instantiating this class will load and initialize a config parser instance.
    """

    def __init__(self, config_dir_path: str) -> None:
        """

        Args:
            config_dir_path: path to a folder containing .pypants.cfg file

        """
        self.config_dir_path = config_dir_path
        self._pants_cfg_path = Path(config_dir_path).joinpath(".pypants.cfg")
        self._config = ConfigParser()
        self._config["project"] = {}
        self._config["package"] = {}
        if self._pants_cfg_path.is_file():
            self._config.read(self._pants_cfg_path)

    def set(self, *args) -> None:
        """Proxy method to set a value on the underlying config parser instance"""
        self._config.set(*args)

    # Project options

    @property
    def ignore_dirs(self) -> Set[str]:
        """Never look for or process files in these directories"""
        return frozenset(
            json.loads(self._config.get("project", "ignore_dirs", fallback="[]"))
        )

    @property
    def ignore_targets(self) -> Set[str]:
        """Set of target package names to ignore when collecting build targets"""
        return frozenset(
            json.loads(self._config.get("project", "ignore_targets", fallback="[]"))
        )

    @property
    def python_package_name_prefix(self) -> str:
        """Prefix to use for names of packages generated by pypants"""
        return self._config.get("project", "python_package_name_prefix", fallback="")

    @property
    def third_party_import_map_path(self) -> Path:
        """Path to the location of the import-map.json file relative to the project root"""
        return Path(
            self._config.get(
                "project",
                "third_party_import_map_path",
                fallback="3rdparty/python/import-map.json",
            )
        )

    @property
    def third_party_requirements_path(self) -> Path:
        """Path to the requirements.txt relative to the project root"""
        return Path(
            self._config.get(
                "project",
                "third_party_requirements_path",
                fallback="3rdparty/python/requirements.txt",
            )
        )

    @property
    def top_dirs(self) -> List[str]:
        """Top-level directories to search for Python packages"""
        return json.loads(self._config.get("project", "top_dirs", fallback="['.']"))

    # Package options

    @property
    def extra_dependencies(self) -> Set[str]:
        """Extra set of dependencies to include in the python_library target"""
        return set(
            json.loads(self._config.get("package", "extra_dependencies", fallback="[]"))
        )

    @property
    def extra_tags(self) -> Set[str]:
        """Extra set of tags to include in the Pants build targets"""
        return set(json.loads(self._config.get("package", "extra_tags", fallback="[]")))

    @property
    def generate_build_file(self) -> bool:
        """Flag denoting whether to generate a BUILD file"""
        return self._config.getboolean("package", "generate_build_file", fallback=True)

    @property
    def generate_local_binary(self) -> bool:
        """Flag denoting whether to generate a python_binary target for local.py"""
        return self._config.getboolean(
            "package", "generate_local_binary", fallback=False
        )

    @property
    def generate_pytest_binary(self) -> bool:
        """Flag denoting whether to include a python_binary target for pytest"""
        return self._config.getboolean(
            "package", "generate_pytest_binary", fallback=False
        )

    @property
    def include_test_coverage(self) -> bool:
        """Flag denoting whether to include a coverage attribute on pytest targets"""
        return self._config.getboolean(
            "package", "include_test_coverage", fallback=True
        )

    @property
    def type(self) -> Optional[str]:
        """Package type.

        Returning none means we should use a heuristic to figure out the type.
        """
        return self._config.get("package", "type", fallback=None)


# Create a singleton for the project configuration
PROJECT_CONFIG = Config(get_git_top_level_path())
