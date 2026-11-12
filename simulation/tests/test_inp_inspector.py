import unittest
from pathlib import Path

from simulation.engine.inp_inspector import inspect_inp


NETWORK_PATH = (
    Path(__file__).resolve().parents[1] / "networks" / "aquatwin_demo.inp"
)


class InpInspectorTests(unittest.TestCase):
    def test_inspects_demo_network(self) -> None:
        summary = inspect_inp(NETWORK_PATH)

        self.assertEqual(summary.name, "aquatwin_demo")
        self.assertEqual(summary.junctions, 4)
        self.assertEqual(summary.reservoirs, 1)
        self.assertEqual(summary.pipes, 6)
        self.assertEqual(summary.total_nodes, 5)
        self.assertEqual(summary.total_links, 6)

    def test_rejects_non_inp_file(self) -> None:
        with self.assertRaises(ValueError):
            inspect_inp(Path(__file__))


if __name__ == "__main__":
    unittest.main()

