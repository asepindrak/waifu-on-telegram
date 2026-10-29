import unittest
import sys
from io import StringIO
from unittest.mock import patch
import bin.cli as cli

class TestCliHelpAndTypo(unittest.TestCase):
    def test_typo_suggestion_udate(self):
        """Verify that typo 'udate' suggests 'update' and displays clean command list."""
        buf = StringIO()
        with patch("sys.stdout", buf):
            cli.print_cli_help(unknown_cmd="udate")
        output = buf.getvalue()
        self.assertIn("Mungkin maksud kamu: 'waifu update'?", output)
        self.assertIn("DAFTAR PERINTAH RESMI", output)
        self.assertIn("waifu start", output)
        self.assertIn("waifu status", output)
        self.assertIn("waifu update", output)

    def test_typo_suggestion_setpu(self):
        """Verify that typo 'setpu' suggests 'setup'."""
        buf = StringIO()
        with patch("sys.stdout", buf):
            cli.print_cli_help(unknown_cmd="setpu")
        output = buf.getvalue()
        self.assertIn("Mungkin maksud kamu: 'waifu setup'?", output)

    def test_completely_unknown_command(self):
        """Verify that completely unknown command shows clean not recognized error without crash."""
        buf = StringIO()
        with patch("sys.stdout", buf):
            cli.print_cli_help(unknown_cmd="xyz12345nonexistent")
        output = buf.getvalue()
        self.assertIn("Perintah 'xyz12345nonexistent' tidak dikenali", output)
        self.assertIn("DAFTAR PERINTAH RESMI", output)

if __name__ == "__main__":
    unittest.main()
