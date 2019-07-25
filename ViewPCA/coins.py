# -*- coding: utf-8 -*-

import os
from collections import OrderedDict
from multiprocessing import Pool, cpu_count

import numpy as np
from PySide2.QtCore import QObject, Signal


def read_spectrum(path):
    return np.loadtxt(path, delimiter=";", usecols=1)


class Coins(QObject):
    new_spectrum = Signal(object, object)

    def __init__(self):
        QObject.__init__(self)

        self.working_directory = ""

        self.coins_tag = np.array([])
        self.spectrum = np.array([])
        self.labels = []

        n_cpu_cores = cpu_count()

        print("number of cpu cores: ", n_cpu_cores)

        self.pool = Pool(processes=n_cpu_cores)

    def load_file(self, path):
        self.working_directory = os.path.dirname(path)

        print("coins working directory: ", self.working_directory)

        self.coins_tag = np.genfromtxt(path, delimiter=";", dtype=str).T

        print("coins tag matrix shape: ", self.coins_tag.shape)

        self.spectrum, self.labels = self.get_spectrum()

        self.new_spectrum.emit(self.spectrum, self.labels)

    def get_spectrum(self):
        spectrum = []
        labels = []
        f_list = []

        for row in self.coins_tag:
            for n, col in enumerate(row):
                if n > 0:
                    f_path = os.path.join(self.working_directory, col + ".txt")

                    if os.path.isfile(f_path):
                        labels.append(row[0])

                        f_list.append(f_path)
                    else:
                        print("file not found: ", f_path)

        spectrum = self.pool.map(read_spectrum, f_list)

        labels = list(OrderedDict.fromkeys(labels))
        spectrum = np.asarray(spectrum)

        print("spectrum shape: ", spectrum.shape)

        """
            In order to the average fast we reshape the matrix in a higher dimensionality. It is now a cube where
            each horizontal slice is a mtrix with 3 rows and spectrum.shape[1] columns. The number of slices is
            int(spectrum.shape[0] / 3). After the reshape the average of each 3 measurements can be done applying
            np.mean in the axis = 1 (the one with 3 rows)
        """

        spectrum = spectrum.reshape(int(spectrum.shape[0] / 3), 3, spectrum.shape[1])

        avg_spectrum = np.mean(spectrum, axis=1)

        return avg_spectrum, labels
