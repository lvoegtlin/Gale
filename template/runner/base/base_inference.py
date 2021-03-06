"""
This file is the template for the boilerplate of train/test of a DNN for image classification

There are a lot of parameter which can be specified to modify the behaviour and they should be used
instead of hard-coding stuff.
"""
# Utils
import base64
import io
import logging
import os

# Delegated
import torch
from PIL import Image

from template.runner.base import AbstractRunner
from template.runner.base.base_routine import BaseRoutine
from template.runner.base.base_setup import BaseSetup
import util.transforms as T
from util.misc import pil_loader, convert_to_rgb


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
            self.model.eval()
            checkpoint = self._load_checkpoint(**kwargs)
            if 'test_transform' in checkpoint:
                self.transform = checkpoint['test_transform']
            else:
                logging.info("Test transform not found in checkpoint. Using ToTensor().")
                self.transform = T.Compose([T.ToTensor()])

            self.classes = checkpoint['classes']

        if pre_load:
            # Check no images to process are given
            assert kwargs['input_image'] is None
            assert kwargs['input_folder'] is None
            # Create a fake empty image to process
            buffered = io.BytesIO()
            Image.new('RGB', (128, 128)).save(buffered, format="PNG")
            kwargs['input_image'] = base64.b64encode(buffered.getvalue()).decode('utf-8')

        # Load and preprocess the data
        img = self.preprocess(**kwargs)

        # Forward Pass
        with torch.no_grad():
            output = self.model(img)

        if pre_load:
            # Return a standard answer
            payload = {'result': "successfully loaded the model"}
            logging.info(f"Returning payload: {payload}")
            return payload
        else:
            # Return post-processed output
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
        return torch.load(load_model, map_location='cpu')

    def preprocess(self, input_folder, input_image, **kwargs):
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
        # Load the image from file system from the path specifiec
        if input_folder is not None:
            assert input_image is None
            img = self._load_image(input_folder)

        # Load the image from base64 passed as parameter
        if input_image is not None:
            assert input_folder is None
            img = Image.open(io.BytesIO(base64.decodebytes(input_image.encode("utf-8"))))
            img = convert_to_rgb(img)

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
            raise FileNotFoundError(f"Could not find file {input_folder}")
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


