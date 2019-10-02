"""
This file is the template for the boilerplate of train/test of a DNN for image classification

There are a lot of parameter which can be specified to modify the behaviour and they should be used
instead of hard-coding stuff.
"""
# Utils
import logging
import os
import numpy as np

# Delegated
import torch

from template.runner.base import AbstractRunner
from template.runner.base.base_routine import BaseRoutine
from template.runner.base.base_setup import BaseSetup
from util.misc import pil_loader

class BaseInference(AbstractRunner):

    def __init__(self):
        """
        Attributes
        ----------
        setup = BaseSetup
            (strategy design pattern) Object responsible for setup operations
        """
        self.setup = BaseSetup()

    def single_run(self, pre_load, **kwargs):
        """ Performs inference only

        Parameters
        ----------
        pre_load : bool
            Flag for only loading the model

        Returns
        -------
        The output of the inference
        """
        # Load the model if it does not exist yet
        if not hasattr(self, 'model') or not hasattr(self, 'transform'):
            self.model = self.setup.setup_model(**kwargs)
            checkpoint = self._load_checkpoint(**kwargs)
            self.transform = checkpoint['test_transform']
            self.classes = checkpoint['classes']

        if not pre_load:
            # Load and preprocess the data
            img = self.preprocess(**kwargs)

            # Forward Pass
            output = self.model(img)

            # Return postprocessed output
            return self.postprocess(output, **kwargs)

    ####################################################################################################################
    """
    These methods delegate their function to other classes in this package.
    It is useful because sub-classes can selectively change the logic of certain parts only.
    """
    def _load_checkpoint(self, load_model, **kwargs):
        """Load a torch checkpoint a return it

        Parameters
        ----------
        load_model : str
            Path to the checkpoint.pth.tar

        Returns
        -------
            A dictionary containing the loaded checkpoint
        """
        return torch.load(load_model)

    def preprocess(self, input_folder, **kwargs):
        """Load and prepares the data to be fed to the neural network

        Parameters
        ----------
        input_folder : str
            Path to the image to process

        Returns
        -------
        img : torch.Tensor | torch.cuda.Tensor
            The loaded and preprocessed image and moved to the correct device
        """
        # Load the image
        img = self._load_image(input_folder)
        # Transform it
        img = self.transform(img)
        # Move it to the correct device
        img, _ = BaseRoutine.move_to_device(input=img, **kwargs)
        # Fake a mini-batch of size 1
        img = img.unsqueeze(0)
        return img

    def _load_image(self, input_folder):
        """Load the image from the file system"""
        if not os.path.exists(input_folder):
            raise FileNotFoundError
        img = pil_loader(input_folder)
        return img

    def postprocess(self, output, **kwargs) -> dict:
        """Post process the output of the network and prepare the payload for the response"""
        # Softmax, argmax then resolve class name and add the activation
        output = torch.nn.Softmax(dim=1)(output)
        value, index = torch.max(output, 1)
        result = [self.classes[index], f"{value.item():.2f}"]
        payload = {'result': result}
        logging.info(f"Returning payload: {payload}")
        return payload

