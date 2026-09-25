import unittest
from pathlib import Path


CPP_SOURCE = (
    Path(__file__).parents[1]
    / "components"
    / "ble_mi_remote"
    / "ble_mi_remote.cpp"
).read_text()
HEADER_SOURCE = (
    Path(__file__).parents[1]
    / "components"
    / "ble_mi_remote"
    / "ble_mi_remote.h"
).read_text()
PYTHON_SOURCE = (
    Path(__file__).parents[1]
    / "components"
    / "ble_mi_remote"
    / "__init__.py"
).read_text()


def function_body(source: str, signature: str) -> str:
    start = source.index(signature)
    opening_brace = source.index("{", start)
    depth = 0

    for index in range(opening_brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening_brace + 1 : index]

    raise AssertionError(f"Unterminated function: {signature}")


class DisconnectPolicyTest(unittest.TestCase):
    def test_disconnect_preserves_bond_and_starts_reconnect_advertising(self) -> None:
        body = function_body(CPP_SOURCE, "void BleMiRemote::onDisconnect(")

        self.assertNotIn("NimBLEDevice::delete", body)
        self.assertNotIn("startPlainAdvertising()", body)
        self.assertIn("startReconnectAdvert()", body)

    def test_manual_plain_advertising_remains_the_bond_reset_path(self) -> None:
        body = function_body(CPP_SOURCE, "void BleMiRemote::plainAdvertStart(")

        self.assertIn("deleteAllBonds()", body)
        self.assertIn("startPlainAdvertising()", body)


class BondPersistenceConfigurationTest(unittest.TestCase):
    def test_required_nimble_security_and_role_options_are_explicit(self) -> None:
        expected_options = {
            'add_idf_sdkconfig_option("CONFIG_BT_NIMBLE_SECURITY_ENABLE", True)',
            'add_idf_sdkconfig_option("CONFIG_BT_NIMBLE_ROLE_PERIPHERAL", True)',
            'add_idf_sdkconfig_option("CONFIG_BT_NIMBLE_ROLE_CENTRAL", True)',
            'add_idf_sdkconfig_option("CONFIG_BT_NIMBLE_NVS_PERSIST", True)',
            'add_idf_sdkconfig_option("CONFIG_BT_NIMBLE_MAX_BONDS", 3)',
        }

        for option in expected_options:
            with self.subTest(option=option):
                self.assertIn(option, PYTHON_SOURCE)


class BondDiagnosticsTest(unittest.TestCase):
    def test_setup_logs_nimble_config_and_restored_bonds(self) -> None:
        body = function_body(CPP_SOURCE, "void BleMiRemote::setup(")

        self.assertIn("bool nimble_ok = NimBLEDevice::init(deviceName)", body)
        self.assertIn("CONFIG_BT_NIMBLE_NVS_PERSIST = ENABLED", body)
        self.assertIn("CONFIG_BT_NIMBLE_SECURITY_ENABLE = ENABLED", body)
        self.assertIn("NimBLEDevice::getNumBonds()", body)
        self.assertIn("NimBLEDevice::getBondedAddress(i)", body)


class TargetAddressPersistenceTest(unittest.TestCase):
    def test_target_address_type_is_persisted_with_the_mac(self) -> None:
        load_body = function_body(CPP_SOURCE, "void BleMiRemote::loadTargetMac(")
        learn_body = function_body(CPP_SOURCE, "void BleMiRemote::learnTargetMac(")

        self.assertIn("_target_addr_type", HEADER_SOURCE)
        self.assertIn("_target_addr_type_pref", HEADER_SOURCE)
        self.assertIn("_target_addr_type_pref.load", load_body)
        self.assertIn("addr.getType()", learn_body)
        self.assertIn("_target_addr_type_pref.save", learn_body)

    def test_reconnect_paths_do_not_force_the_target_to_public(self) -> None:
        self.assertNotIn("_target_mac, BLE_ADDR_PUBLIC", CPP_SOURCE)

        for signature in (
            "void BleMiRemote::connectWakeStart(",
            "void BleMiRemote::startReconnectAdvert(",
            "void BleMiRemote::fireDirectedBurst(",
        ):
            with self.subTest(signature=signature):
                body = function_body(CPP_SOURCE, signature)
                self.assertIn("_target_addr_type", body)

    def test_successful_authentication_learns_the_identity_address(self) -> None:
        body = function_body(CPP_SOURCE, "void BleMiRemote::onAuthenticationComplete(")

        self.assertIn("connInfo.getIdAddress()", body)
        self.assertIn("learnTargetMac", body)


if __name__ == "__main__":
    unittest.main()
