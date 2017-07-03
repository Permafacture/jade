# -*- coding: utf-8 -*-
#
# Learner utilities.
#
# @author <bprinty@gmail.com>
# ----------------------------------------------


# imports
# -------
import os
import re
import numpy
import warnings
from sklearn.base import BaseEstimator
from sklearn.svm import SVC
from sklearn.externals import joblib
from gems import composite

from .transform import CompositeTransform


# model building
# --------------
class Learner(BaseEstimator):
    """
    Machine-learning from arbitrary vectorizer. This object also
    allows for swapping different models/features and doing grid
    searches to obtain optimal parameters for models.

    Args:
        transform (Transform, list): Transform to apply to data to convert
            targets and responses into a ai-readable format.
        model (obj): Classifier to use in learning.
    """
    _X = None
    _Y = None
    _Z = None

    def __init__(self, transform, model=SVC()):
        # use composite transform for everything, so that
        # simulation processors can be skipped during prediction
        transform = CompositeTransform(transform)
        self.vectorizer = transform
        self.model = model
        return

    @classmethod
    def from_config(cls, filename):
        """
        TODO: THIS
        """
        return

    @classmethod
    def load(cls, filename):
        """
        Load model pickle.

        Args:
            filename (str): Name of known model to load, or filename
                for model pickle or config file.
        """
        global session
        # try loading file directly
        if os.path.exists(filename):
            try:
                return joblib.load(filename)
            except:
                return cls.from_config(filename)
        
        # try loading pickle from models directory
        elif os.path.exists(os.path.join(session.models, filename + '.pkl')):
            return joblib.load(os.path.join(session.models, filename + '.pkl'))

        # try loading config from models directory
        elif os.path.exists(os.path.join(session.models, filename + '.yml')):
            return cls.from_config(os.path.join(session.models, filename + '.yml'))

        else:
            raise AssertionError('Cannot load model. Pickle file does not exist!')
        return

    def save(self, filename, archive=False):
        """
        Save learner model to file.

        Args:
            filename (str): Name of known model to save to, or filename
                for model pickle or config file.
            archive (bool): If true, save model in internal models directory,
                using filename as the name of the model. This should be used
                only during model development.
        """
        if archive:
            filename = os.path.basename(filename)
            filename = os.path.join(session.models, filename + '.pkl')
        joblib.dump(
            self.__class__(
                transform=self.vectorizer.clone(),
                model=self.model
            ), filename
        )
        return

    def flatten(self, X, Y):
        """
        "Flatten" input, changing dimensionality into
        something conducive to AI model development. In a nutshell,
        this decreases the dimensionality of predictors and responses
        until the response vector is one-dimensional.
        """
        fX, fY, fZ = [], [], []
        if isinstance(Y, (list, tuple, numpy.ndarray)):
            for idx in range(0, len(X)):
                dat = self.flatten(X[idx], Y[idx])
                fX.extend(dat[0])
                fY.extend(dat[1])
                fZ.append(len(X[idx]))
        else:
            return [X], [Y]
        return numpy.array(fX), numpy.array(fY), fZ

    def inverse_flatten(self, X, Y, Z):
        """
        "Inverse flatten" input, changing dimensionality back into
        space that can be back-transformed into something
        human-interpretable.
        """
        fX, fY = [], []
        if len(Z) < len(Y):
            tY, tX = [], []
            cidx = 0
            for iz, z in enumerate(Z):
                tX.append(X[cidx:(cidx + z)])
                tY.append(Y[cidx:(cidx + z)])
                cidx = cidx + z
            X, Y = numpy.array(tX), numpy.array(tY)
        return X, Y

    def transform(self, X, Y=None):
        """
        Transform input data into ai-ready tensor.
        """
        obj = self.vectorizer.clone()
        X, Y = obj.fit_transform(X, Y)
        return X, Y

    def fit(self, X, Y):
        """
        Train learner for speicific data indices.
        """
        tX, tY = self.vectorizer.fit_transform(X, Y)
        self._X, self._Y, self._Z = self.flatten(tX, tY)
        self.model.fit(self._X, self._Y)
        return self

    def fit_transform(self, X, Y):
        self.fit(X, Y)
        return self._X, self._Y

    def fit_predict(self, X, Y):
        """
        Fit models to data and return prediction.
        """
        self.fit(X, Y)
        pY = self.model.predict(self._X)
        fX, fY = self.inverse_flatten(self._X, pY, self._Z)
        rX, rY = self.vectorizer.inverse_fit_transform(fX, fY)
        return rY

    def predict(self, X):
        """
        Predict results from new data.
        """
        if self._Y is None:
            raise AssertionError('Model has not been fit! Cannot make predictions for new data.')
        obj = self.vectorizer.clone()
        tX, tY = obj.fit_transform(X, self._Y, pred=True)
        fX, fY, fZ = self.flatten(tX, tY)
        pY = self.model.predict(fX)
        fX, fY = self.inverse_flatten(fX, pY, fZ)
        rX, rY = obj.inverse_fit_transform(fX, pY)
        return rY
