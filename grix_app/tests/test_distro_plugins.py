import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from grix.modules import diagnostics
from grix.modules.plugins import PluginAPI, _Registry


ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = ROOT / "plugins"
sys.path.insert(0, str(PLUGIN_ROOT))
from _shared import dnf_support

PLUGIN_PATHS = {
    name: PLUGIN_ROOT / name / "plugin.py"
    for name in ("arch_pacman", "fedora_dnf", "rpm_family")
}


def load_plugin(plugin_id):
    spec = importlib.util.spec_from_file_location(
        f"test_plugin_{plugin_id}", PLUGIN_PATHS[plugin_id]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class DistributionPluginTests(unittest.TestCase):
    def test_platform_plugins_replace_only_their_distro_specific_checks(self):
        plugin_predicates = {
            "arch_pacman": ("_is_arch_based", {"arch"}),
            "fedora_dnf": (None, {"fedora"}),
            "rpm_family": (None, {"rocky"}),
        }
        expected_replacements = {
            "package_manager",
            "updates",
            "security",
            "old_kernels",
        }

        for plugin_id, (predicate, distro_ids) in plugin_predicates.items():
            with self.subTest(plugin=plugin_id):
                module = load_plugin(plugin_id)
                registry = _Registry()
                if predicate:
                    platform_patch = patch.object(module, predicate, return_value=True)
                else:
                    platform_patch = patch.object(
                        dnf_support, "_distribution_ids", return_value=distro_ids
                    )
                with platform_patch, patch.object(
                    dnf_support.shutil, "which", return_value="/usr/bin/dnf"
                ):
                    module.register(PluginAPI(registry, plugin_id))

                self.assertEqual(registry.replaced_check_ids, expected_replacements)
                self.assertEqual(len(registry.lesson_tracks), 1)
                self.assertGreaterEqual(len(registry.checks), 5)

    def test_non_target_plugins_do_not_replace_builtin_checks(self):
        plugin_predicates = {
            "arch_pacman": "_is_arch_based",
        }
        for plugin_id, predicate in plugin_predicates.items():
            with self.subTest(plugin=plugin_id):
                module = load_plugin(plugin_id)
                registry = _Registry()
                with patch.object(module, predicate, return_value=False):
                    module.register(PluginAPI(registry, plugin_id))
                self.assertFalse(registry.replaced_check_ids)
                self.assertFalse(registry.checks)
        for plugin_id in ("fedora_dnf", "rpm_family"):
            with self.subTest(plugin=plugin_id):
                module = load_plugin(plugin_id)
                registry = _Registry()
                with patch.object(dnf_support, "_distribution_ids", return_value=set()), patch.object(
                    dnf_support.shutil, "which", return_value="/usr/bin/dnf"
                ):
                    module.register(PluginAPI(registry, plugin_id))
                self.assertFalse(registry.replaced_check_ids)
                self.assertFalse(registry.checks)

    def test_dnf_update_results_offer_the_allowlisted_upgrade_command(self):
        output = "kernel-core.x86_64 6.10.1-1.fc41 updates"
        for plugin_id, check_name in (
            ("fedora", "_check_updates"),
            ("rpm", "_check_updates"),
        ):
            with self.subTest(plugin=plugin_id):
                with patch.object(dnf_support, "_run", return_value=(100, output, "")):
                    result = getattr(dnf_support, check_name)(plugin_id)
                self.assertEqual(result.status, diagnostics.Status.YELLOW)
                self.assertIn("--assumeyes", result.fixes[0].commands[0])

    def test_dnf_package_checks_distinguish_lock_errors_from_dependency_issues(self):
        for plugin_id, check_name in (
            ("fedora", "_check_package_manager"),
            ("rpm", "_check_package_manager"),
        ):
            with self.subTest(plugin=plugin_id, outcome="lock"):
                with patch.object(
                    dnf_support,
                    "_run",
                    return_value=(1, "", "Another app is currently holding the DNF lock"),
                ):
                    result = getattr(dnf_support, check_name)(plugin_id)
                self.assertEqual(result.status, diagnostics.Status.UNKNOWN)
                self.assertFalse(result.fixes)
            with self.subTest(plugin=plugin_id, outcome="dependency"):
                with patch.object(
                    dnf_support,
                    "_run",
                    return_value=(1, "Problem: package app requires missing-lib", ""),
                ):
                    result = getattr(dnf_support, check_name)(plugin_id)
                self.assertEqual(result.status, diagnostics.Status.RED)
                self.assertIn("distro-sync", result.fixes[0].commands[0])

    def test_arch_update_repair_uses_full_system_upgrade(self):
        module = load_plugin("arch_pacman")
        with patch.object(module, "_run", return_value=(0, "linux 6.10 -> 6.11", "")):
            result = module.check_arch_updates()
        self.assertEqual(result.status, diagnostics.Status.YELLOW)
        self.assertEqual(
            result.fixes[0].commands,
            ["sudo pacman -Syu --noconfirm"],
        )

    def test_dnf_orphan_check_excludes_explicitly_installed_packages(self):
        dependency = "lib-unused-0:1.0-1.fc41.x86_64"
        application = "my-app-0:2.0-1.fc41.x86_64"
        outputs = [
            (0, f"{dependency}\n{application}", ""),
            (0, application, ""),
        ]
        for plugin_id in ("fedora", "rpm"):
            with self.subTest(plugin=plugin_id):
                with patch.object(dnf_support, "_run", side_effect=outputs):
                    result = dnf_support._check_unneeded_dependencies(plugin_id)
                self.assertEqual(result.status, diagnostics.Status.YELLOW)
                self.assertEqual(
                    [option.id for option in result.fixes[0].options],
                    [dependency],
                )

    def test_privileged_plugin_repairs_map_to_validated_helper_actions(self):
        commands = {
            "pacman -Syu --noconfirm": "grix-helper pacman-upgrade",
            "pacman -Sc --noconfirm": "grix-helper pacman-clean-cache",
            "dnf upgrade --refresh --assumeyes": "grix-helper dnf-upgrade",
            "dnf distro-sync --assumeyes": "grix-helper dnf-distro-sync",
            "dnf clean all": "grix-helper dnf-clean-cache",
            "dnf remove --oldinstallonly --assumeyes":
                "grix-helper dnf-remove-old-kernels",
            "systemctl enable --now firewalld":
                "grix-helper enable-firewalld",
            "pacman -Rns package-name":
                "grix-helper pacman-remove package-name",
            "dnf remove --assumeyes --setopt=clean_requirements_on_remove=False package-0:1.0-1.fc41.x86_64":
                "grix-helper dnf-remove package-0:1.0-1.fc41.x86_64",
        }
        with patch.object(diagnostics, "_have_grix_helper", return_value=True):
            for command, expected in commands.items():
                with self.subTest(command=command):
                    self.assertEqual(
                        diagnostics._to_helper_invocation(command),
                        expected,
                    )


if __name__ == "__main__":
    unittest.main()
