import enum
from typing import Optional, Tuple
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from database import BLOCKCHAIN, Database
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np


class ViewMode(enum.Enum):
    ASCII_HISTOGRAM = "ascii_histogram"
    MAGIC_FILE_HISTOGRAM = "magic_file_histogram"
    IMGHDR_FILE_HISTOGRAM = "imghdr_file_histogram"


class View:
    def get_matplotlib_color_from_blockchain(self) -> str:
        if self._blockchain is not None:
            if "monero" in self._blockchain.value:
                return "black"
            elif "eth" in self._blockchain.value:
                return "blue"
            elif "bitcoin" in self._blockchain.value:
                return "orange"
        return "mediumblue"

    def ascii_histogram(self):
        result = self._database.ascii_histogram(self._blockchain)
        lengths = np.array(list(map(lambda item: item[0], result)))
        counts = np.array(list(map(lambda item: item[1], result)))
        x_pos = np.arange(len(lengths))

        lengths_histogram_no_gaps = []
        counts_histogram_no_gaps = []
        for i in range(10, np.max(lengths)+1):
            lengths_histogram_no_gaps.append(i)
            if i in lengths:
                counts_histogram_no_gaps.append(int(counts[np.where(lengths == i)]))
            else:
                counts_histogram_no_gaps.append(0)

        accumulated_string_count = []
        for i in range(34):
            accumulated_string_count.append(np.sum(counts_histogram_no_gaps[i:]))
        accumulated_string_count = np.array(accumulated_string_count)
        minimum_string_lengths= np.arange(10, 10+34)
        x2_pos = np.arange(34)

        color = self.get_matplotlib_color_from_blockchain()

        fig_axis_tuple: Tuple[Figure, Tuple[Axes, Axes]] = plt.subplots(2)
        fig, (ax1, ax2) = fig_axis_tuple
        ax1.bar(x_pos, counts, color=color)
        ax1.set_xticks(x_pos, lengths)
        ax1.set_xlabel("string length")
        ax1.set_yscale("log")
        ax1.set_ylabel("counts")
        ax1.set_title(self._blockchain.value + " Count of each detected string length")

        ax2.bar(x2_pos, accumulated_string_count, color=color)
        ax2.set_xticks(x2_pos, minimum_string_lengths)
        ax2.set_xlabel("minimum string length")
        ax2.set_yscale("log")
        ax2.set_ylabel("counts")
        ax2.set_title(self._blockchain.value + " Count of detected strings with a minimum length")

        plt.savefig("asci_histogram_" + self._blockchain.value, dpi=300)
        plt.show()

    def magic_file_histogram(self):
        result = self._database.magic_file_histogram(self._blockchain)
        print(result)

    def imghdr_file_histogram(self):
        result = self._database.imghdr_file_histogram(self._blockchain)
        print(result)

    def __init__(self, blockchain: Optional[BLOCKCHAIN], database: Database):
        self._blockchain = blockchain
        self._database = database

    def view(self, mode: ViewMode) -> None:
        if mode == ViewMode.ASCII_HISTOGRAM:
            self.ascii_histogram()
        elif mode == ViewMode.MAGIC_FILE_HISTOGRAM:
            self.magic_file_histogram()
