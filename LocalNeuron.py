from math import ceil, exp
from random import randint


class NeuroNetwork:
    def __init__(self, input_l_size, output_l_size, hidden_layers_count=1):
        self.layers = []
        self.selected_layer = None
        self.activate_func = NeuroNetwork.sigmoid
        self.l_count = hidden_layers_count + 2
        hidden_l_size = min(input_l_size * 2 - 1, ceil(input_l_size * 2 / 3 + output_l_size))

        for i in range(self.l_count):
            self.layers[i] = self.add_layer(i, input_l_size, output_l_size, hidden_l_size)

        self.selected_layer = None  # "чистим" указатель

    def get_prediction(self):
        output_layer = self.layers[self.l_count - 1].neurons
        outputs = []
        for i in output_layer:
            outputs.append(i.get_value())
        return outputs

    @staticmethod
    def sigmoid(x):
        return 1 / (1 + exp(-x))

    def add_layer(self, i, in_size, out_size, hl_size):
        count = i + 1

        if 1 < count < self.l_count:
            self.selected_layer = Layer(hl_size, self.selected_layer, self)
            return self.selected_layer

        if count == 1:
            self.selected_layer = Layer(in_size, None, self)
            return self.selected_layer

        self.selected_layer = Layer(out_size, self.selected_layer, self)
        return self.selected_layer

    def train(self, dataset, iters=1000):
        print(f'\nTRAINING STARTED({iters} iterations)...')
        for _ in range(iters):
            self.train_once(dataset)
        print(f'\nTRAINING COMPLETED!\n')

    def set_input_data(self, val_list):
        self.layers[0].set_input_data(val_list)

    def train_once(self, dataset):
        for case in dataset:
            datacase = {'in_data': case[0], 'res': case[1]}

            self.set_input_data(datacase['in_data'])
            curr_res = self.get_prediction()
            for i in range(len(curr_res)):
                self.layers[self.l_count - 1].neurons[i].set_error(curr_res[i] - datacase['res'])


class Layer:
    def __init__(self, layer_size, prev_layer, parent_network):
        self.prev_layer = prev_layer
        self.network = parent_network
        self.neurons = [Neuron(self, prev_layer) for _ in range(layer_size)]

    def set_input_data(self, val_list):
        for i in range(len(val_list)):
            self.neurons[i].set_value(val_list[i])


class Neuron:
    def __init__(self, layer: Layer, previous_layer: Layer):
        self.value = 0
        self._layer = layer
        self.inputs = [Input(prev_neuron, randint(0, 10) / 10) for prev_neuron in
                       previous_layer.neurons] if previous_layer else []

        self.get_value()


    def set_error(self):
        

    def is_no_inputs(self):
        return not self.inputs

    def set_value(self, value):
        self.value = value

    def get_input_sum(self):
        return sum((i.weight * i.prev_neuron.get_value()) for i in self.inputs)

    def get_value(self):
        network = self._layer.network
        if not self.is_no_inputs():
            self.set_value(network.activate_func(self.get_input_sum()))
        return self.value


class Input:
    def __init__(self, prev_neuron: Neuron, weight):
        self.prev_neuron = prev_neuron
        self.weight = weight


new_nw = NeuroNetwork(2, 1)
dataset_or = [[[0, 0], 0], [[0, 1], 1], [[1, 0], 1], [[1, 1], 1]]
new_nw.train(dataset_or, 100000)
