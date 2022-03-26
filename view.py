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
    RECORD_STATS = "record_stats"


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

    def ascii_histogram_complete(self):
        result = self._database.ascii_histogram(self._blockchain)
        lengths = np.array(list(map(lambda item: item[0], result)))
        counts = np.array(list(map(lambda item: item[1], result)))

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

        print(accumulated_string_count, minimum_string_lengths)
        x_pos = np.arange(len(lengths))

        compact_length_labels = [" " for _ in range(len(lengths))]
        for i in range(len(lengths)):
            if i == 0:
                compact_length_labels[0] = str(lengths[0])
            # add 10 more labels interspersed in the histogram
            if (i % (int(len(lengths) / 15))) == 0:
                compact_length_labels[i] = lengths[i]
        compact_length_labels[-1] = str(lengths[-1])
        compact_length_labels = np.array(compact_length_labels)

        # print(x_pos, lengths, compact_length_labels, len(x_pos), len(lengths), len(compact_length_labels))

        fig_axis_tuple: Tuple[Figure, Tuple[Axes, Axes]] = plt.subplots(2)
        fig, (ax1, ax2) = fig_axis_tuple
        ax1.bar(x_pos, counts, color=color)
        ax1.set_xticks(x_pos, compact_length_labels)
        ax1.set_xlabel("string length")
        ax1.set_yscale("log")
        ax1.set_ylabel("counts")
        # ax1.set_title(self._blockchain.value + " Count of each detected string length")
        plt.setp(ax1.get_xticklabels(), fontsize=7, rotation='vertical')

        print(x2_pos, accumulated_string_count, minimum_string_lengths, len(x2_pos), len(accumulated_string_count), len(minimum_string_lengths))

        ax2.bar(x2_pos, accumulated_string_count, color=color)
        ax2.set_xticks(x2_pos, minimum_string_lengths)
        ax2.set_xlabel("minimum string length")
        ax2.set_yscale("log")
        ax2.set_ylabel("counts")
        # ax2.set_title(self._blockchain.value + " Count of detected strings with a minimum length")
        plt.setp(ax2.get_xticklabels(), fontsize=7, rotation='vertical')
        plt.subplots_adjust(hspace=0.43)

        plt.savefig("ascii_histogram_" + self._blockchain.value + ".pdf", dpi=600)
        plt.show()


    def ascii_histogram(self):
        result = self._database.ascii_histogram(self._blockchain)
        lengths = np.array(list(map(lambda item: item[0], result)))
        counts = np.array(list(map(lambda item: item[1], result)))

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

        print(accumulated_string_count, minimum_string_lengths)

        # truncate the histogram at 34 entries
        if len(lengths > 34):
            lengths = lengths[:34]
        if len(counts > 34):
            counts = counts[:34]

        x_pos = np.arange(len(lengths))

        fig_axis_tuple: Tuple[Figure, Tuple[Axes, Axes]] = plt.subplots(2)
        fig, (ax1, ax2) = fig_axis_tuple
        ax1.bar(x_pos, counts, color=color)
        ax1.set_xticks(x_pos, lengths)
        ax1.set_xlabel("string length")
        ax1.set_yscale("log")
        ax1.set_ylabel("counts")
        # ax1.set_title(self._blockchain.value + " Count of each detected string length")
        plt.setp(ax1.get_xticklabels(), fontsize=7, rotation='vertical')

        ax2.bar(x2_pos, accumulated_string_count, color=color)
        ax2.set_xticks(x2_pos, minimum_string_lengths)
        ax2.set_xlabel("minimum string length")
        ax2.set_yscale("log")
        ax2.set_ylabel("counts")
        # ax2.set_title(self._blockchain.value + " Count of detected strings with a minimum length")
        plt.setp(ax2.get_xticklabels(), fontsize=7, rotation='vertical')
        plt.subplots_adjust(hspace=0.43)

        plt.savefig("ascii_histogram_" + self._blockchain.value + ".pdf", dpi=600)
        plt.show()

    def magic_file_histogram(self):
        result = self._database.magic_file_histogram(self._blockchain)
        file_types = np.array(list(map(lambda item: item[0], result)))
        counts = np.array(list(map(lambda item: item[1], result)))

        # remove some more magic file type entries
        filtered_file_types = []
        filtered_counts = []
        utf_count = 0
        jpeg_count = 0
        png_count = 0
        gringotts_count = 0
        dif_count = 0
        tar_archive_count = 0
        openssl_encrypted_count = 0
        os_2_count = 0
        for file_type, count in zip(file_types, counts):
            if count == 1:
                continue
            if "UTF" in file_type:
                utf_count += 1
                continue
            if "JPEG" in file_type:
                jpeg_count += 1
                continue
            if "PNG" in file_type:
                png_count += 1
                continue
            if "Gringotts" in file_type:
                gringotts_count += 1
                continue
            if "DIF" in file_type:
                dif_count += 1
                continue
            if "tar archive" in file_type:
                tar_archive_count += 1
                continue
            if "openssl" in file_type:
                openssl_encrypted_count += 1
                continue
            if "OS/2" in file_type:
                os_2_count += 1
                continue
            if "Windows metafile" in file_type or "Macintosh MFS data" in file_type or "HP PCL" in file_type or "core file (Xenix)" in file_type or "compiled Lisp" in file_type or "Zebra Metafile" in file_type or "StarOffice Gallery" in file_type or "Minix filesystem" in file_type or "Macintosh HFS" in file_type or "MacBinary" in file_type or "Embedded OpenType" in file_type or "DIY-Thermocam" in file_type or "Apple HFS" in file_type or "object file" in file_type or "b.out" in file_type or "RISC OS" in file_type or "MMDF" in file_type or "Lotus" in file_type or "FuseCompress" in file_type or "FIGlet" in file_type or "AppleDouble" in file_type or "AppleSingle" in file_type or "MED_Song" in file_type or "Android binary" in file_type or "GDSII" in file_type or "SunOS" in file_type or "AppledDouble" in file_type or "Core file" in file_type or "MAthematica" in file_type or "Berkeley DB" in file_type or "Microstation" in file_type or "overlay object file" in file_type or "LADS" in file_type or "Netscape" in file_type or "ESRI Shapefile" in file_type or "Cytovision" in file_type or "i960" in file_type or "ddis" in file_type or "SPEC" in file_type or "MMFD" in file_type or "AHX" in file_type or "libfprint" in file_type or "SeqBox" in file_type or "Psion" in file_type or "PCP compiled" in file_type or "separate object" in file_type or "Compiled XKB" in file_type or "dar archive" in file_type or "cisco" in file_type or "Symbian" in file_type or "Spectrum .TAP" in file_type or "StuffIt" in file_type or "Spectrum" in file_type or "Spectrum" in file_type or "RAD" in file_type or "Psion Series" in file_type or "Progressive Graphics" in file_type or "Palm" in file_type or "LFS" in file_type or "GEM" in file_type or "ESRI Shapefile" in file_type or "keymap" in file_type or "Aster*x" in file_type:
                continue
            filtered_file_types.append(file_type)
            filtered_counts.append(count)
        if utf_count > 0:
            filtered_file_types.append("UTF-8")
            filtered_counts.append(utf_count)
        if jpeg_count > 0:
            filtered_file_types.append("JPEG image data")
            filtered_counts.append(jpeg_count)
        if png_count > 0:
            filtered_file_types.append("PNG image data")
            filtered_counts.append(png_count)
        if gringotts_count > 0:
            filtered_file_types.append("Gringotts data file")
            filtered_counts.append(gringotts_count)
        if dif_count > 0:
            filtered_file_types.append("DIF (DVCPRO) movie file")
            filtered_counts.append(dif_count)
        if tar_archive_count > 0:
            filtered_file_types.append("tar archive")
            filtered_counts.append(tar_archive_count)
        if openssl_encrypted_count > 0:
            filtered_file_types.append("openssl enc'd data")
            filtered_counts.append(openssl_encrypted_count)
        if os_2_count > 0:
            filtered_file_types.append("OS/2 graphic")
            filtered_counts.append(os_2_count)
        file_types = np.array(filtered_file_types)
        counts = np.array(filtered_counts)

        print(file_types, counts, len(file_types), len(counts))

        truncated_file_types = []
        for file_type in file_types:
            if len(file_type) > 20:
                truncated_file_types.append(file_type[:19] + ".")
            else:
                truncated_file_types.append(file_type)

        x_pos = np.arange(len(file_types))
        color = self.get_matplotlib_color_from_blockchain()

        fig_axis_tuple: Tuple[Figure, Axes] = plt.subplots(1)
        fig, ax1 = fig_axis_tuple
        ax1.bar(x_pos, counts, color=color)
        ax1.set_xticks(x_pos, truncated_file_types)
        ax1.set_yscale("log")
        ax1.set_ylabel("counts")
        # ax1.set_title(self._blockchain.value + " Count of magic detected file types")
        plt.setp(ax1.get_xticklabels(), fontsize=12, rotation='vertical')
        plt.subplots_adjust(bottom=0.41)
        plt.savefig("magic_file_histogram_" + self._blockchain.value + ".pdf", dpi=600)
        plt.show()
    
    def imghdr_file_histogram(self):
        result = self._database.imghdr_file_histogram(self._blockchain)
        file_types = np.array(list(map(lambda item: item[0], result)))
        counts = np.array(list(map(lambda item: item[1], result)))
        print(file_types, counts, len(file_types), len(counts))

        truncated_file_types = []
        for file_type in file_types:
            if len(file_type) > 20:
                truncated_file_types.append(file_type[:19] + ".")
            else:
                truncated_file_types.append(file_type)

        x_pos = np.arange(len(file_types))
        color = self.get_matplotlib_color_from_blockchain()

        fig_axis_tuple: Tuple[Figure, Axes] = plt.subplots(1)
        fig, ax1 = fig_axis_tuple
        ax1.bar(x_pos, counts, color=color)
        ax1.set_xticks(x_pos, truncated_file_types)
        ax1.set_yscale("log")
        ax1.set_ylabel("counts")
        # ax1.set_title(self._blockchain.value + " Count of imghdr detected file types")
        plt.setp(ax1.get_xticklabels(), fontsize=12, rotation='vertical')
        plt.savefig("imghdr_file_histogram_" + self._blockchain.value + ".pdf", dpi=600)
        plt.show()

    def __init__(self, blockchain: Optional[BLOCKCHAIN], database: Database):
        self._blockchain = blockchain
        self._database = database

    def view(self, mode: ViewMode) -> None:
        if mode == ViewMode.ASCII_HISTOGRAM:
            self.ascii_histogram_complete()
        elif mode == ViewMode.IMGHDR_FILE_HISTOGRAM:
            self.imghdr_file_histogram()
        elif mode == ViewMode.MAGIC_FILE_HISTOGRAM:
            self.magic_file_histogram()
        elif mode == ViewMode.RECORD_STATS:
            stats = self._database.get_record_statistics(self._blockchain)
            print(stats)
