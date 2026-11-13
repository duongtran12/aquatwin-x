import unittest
from pathlib import Path

from simulation.engine.inp_inspector import inspect_inp, read_inp_elements


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

    def test_reads_network_elements(self) -> None:
        elements = read_inp_elements(NETWORK_PATH)

        self.assertEqual(len(elements["nodes"]), 5)
        self.assertEqual(len(elements["links"]), 6)
        self.assertEqual(elements["nodes"][0]["id"], "J1")
        self.assertEqual(elements["links"][0]["source"], "R1")


if __name__ == "__main__":
    unittest.main()

