import unittest
from pathlib import Path


SOURCE = (
    Path(__file__).parents[1]
    / "components"
    / "ble_mi_remote"
    / "ble_mi_remote.cpp"
).read_text()


def function_body(signature: str) -> str:
    start = SOURCE.index(signature)
    opening_brace = SOURCE.index("{", start)
    depth = 0

    for index in range(opening_brace, len(SOURCE)):
        if SOURCE[index] == "{":
            depth += 1
        elif SOURCE[index] == "}":
            depth -= 1
            if depth == 0:
                return SOURCE[opening_brace + 1 : index]

    raise AssertionError(f"Unterminated function: {signature}")


class DisconnectPolicyTest(unittest.TestCase):
    def test_disconnect_preserves_bond_and_starts_reconnect_advertising(self) -> None:
        body = function_body("void BleMiRemote::onDisconnect(")

        self.assertNotIn("NimBLEDevice::delete", body)
        self.assertNotIn("startPlainAdvertising()", body)
        self.assertIn("startReconnectAdvert()", body)

    def test_manual_plain_advertising_remains_the_bond_reset_path(self) -> None:
        body = function_body("void BleMiRemote::plainAdvertStart(")

        self.assertIn("deleteAllBonds()", body)
        self.assertIn("startPlainAdvertising()", body)


if __name__ == "__main__":
    unittest.main()
