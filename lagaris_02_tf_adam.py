"""Demonstration of use of TensorFlow to solve the lagaris02 ODE IVP."""


import datetime
import os
import platform
import sys

import numpy as np

import tensorflow as tf

from nnde.differentialequation.ode.ode1ivp import ODE1IVP
from nnde.math.trainingdata import create_training_grid


def print_system_information():
    print("System report:")
    print(datetime.datetime.now())
    print("Host name: %s" % platform.node())
    print("OS: %s" % platform.platform())
    print("uname:", platform.uname())
    print("Python version: %s" % sys.version)
    print("Python build:", platform.python_build())
    print("Python compiler: %s" % platform.python_compiler())
    print("Python implementation: %s" % platform.python_implementation())
    print("Python file: %s" % __file__)


def create_output_directory():
    path_noext, ext = os.path.splitext(__file__)
    output_dir = path_noext
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    return output_dir


def create_training_data(nt):
    x_train = np.array(create_training_grid(nt))
    return x_train


def build_model(H):
    hidden_layer = tf.keras.layers.Dense(
        units=H, use_bias=True,
        activation=tf.keras.activations.sigmoid,
    )
    output_layer = tf.keras.layers.Dense(
        units=1,
        activation=tf.keras.activations.linear,
        use_bias=False,
    )
    model = tf.keras.Sequential([hidden_layer, output_layer])
    return model


if __name__ == '__main__':

    # Specify the equation to solve.
    eq_module = 'nnde.differentialequation.examples.lagaris_02'
    eq_name = eq_module.split('.')[-1]

    # Specify the training algorithm.
    # trainalg = 'delta'

    # Number of hidden nodes.
    H = 10

    # Number of training points.
    nt = 11

    # Number of training epochs.
    n_epochs = 1000

    # Learning rate.
    learning_rate = 0.01

    # Random number generator seed.
    random_seed = 0

    print_system_information()

    # Set up the output directory.
    output_dir = create_output_directory()

    # Create and save the training data, then convert to Variable.
    xt = create_training_data(nt)
    np.savetxt(os.path.join(output_dir,'training_points.dat'), xt)
    xtv = tf.Variable(xt.reshape((nt, 1)), dtype=tf.float32)

    # Read the equation specification.
    ode1ivp = ODE1IVP(eq_module)

    # Build the model.
    model = build_model(H)

    # Create history variables.
    losses = []
    phist = []

    # Set the random number seed for reproducibility.
    tf.random.set_seed(random_seed)

    # Rename the training Variable for convenience.
    x = xtv

    # Create the optimizer.
    optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate)

    # Train the model.
    print("Hyperparameters: nt = %s, H = %s, n_epochs = %s, learning_rate = %s"
          % (nt, H, n_epochs, learning_rate))
    t_start = datetime.datetime.now()
    print("Training started at", t_start)
    for epoch in range(n_epochs):
        # print("Starting epoch %s." % epoch)

        # Run the forward pass.
        with tf.GradientTape() as tape2:
            with tf.GradientTape() as tape1:

                # Compute the network output.
                N = model(x)

                # Compute trial solution.
                y = x*N

            # Compute the gradient of trial solution the network output wrt
            # the inputs.
            dy_dx = tape1.gradient(y, x)

            # Compute the estimate of the differential equation.
            G = dy_dx + y/5 - tf.math.exp(-x/5)*tf.math.cos(x)

            # Compute the loss function.
            L = tf.reduce_sum(G**2)
        
        # Save the current loss.
        losses.append(L.numpy())

        # Compute the gradient of the loss function wrt the network parameters.
        grad = tape2.gradient(L, model.trainable_variables)

        # Save the parameters used in this pass.
        phist.append(
            np.hstack(
                (model.trainable_variables[0][0].numpy(),    # w (1, H) matrix
                 model.trainable_variables[1].numpy(),       # u (H,) row vector
                 model.trainable_variables[2][:, 0].numpy()) # v (H, 1) column vector
            )
        )

        # Update the parameters for this pass.
        optimizer.apply_gradients(zip(grad, model.trainable_variables))
    
        # print("Ending epoch %s." % epoch)

    t_stop = datetime.datetime.now()
    print("Training stopped at", t_stop)
    t_elapsed = t_stop - t_start
    print("Total training time was %s seconds." % t_elapsed.total_seconds())

    # Save the parameter history.
    np.savetxt(os.path.join(output_dir, 'phist.dat'), np.array(phist))

    # Compute the trained solution and derivative at the training points.
    with tf.GradientTape() as tape:
        N = model(xtv)
    dN_dx = tape.gradient(N, xtv)
    N = tf.reshape(N, (nt, 1))
    dN_dx = tf.reshape(dN_dx, (nt, 1))
    Yt = xtv*N
    np.savetxt(os.path.join(output_dir, 'Yt.dat'), Yt.numpy().reshape((nt)))
    dYt_dx = xtv*dN_dx + N
    np.savetxt(os.path.join(output_dir, 'dYt_dx.dat'), dYt_dx.numpy().reshape((nt)))

    # (Optional) Compute and save the analytical solution and derivative.
    if ode1ivp.Ya:
        Ya = np.array([ode1ivp.Ya(x) for x in xt])
        np.savetxt(os.path.join(output_dir,'Ya.dat'), Ya)
    if ode1ivp.dYa_dx:
        dYa_dx = np.array([ode1ivp.dYa_dx(x) for x in xt])
        np.savetxt(os.path.join(output_dir,'dYa_dx.dat'), dYa_dx)

    # (Optional) Compute and save the error in the trained solution and derivative.
    if ode1ivp.Ya:
        Y_err = Yt.numpy().reshape((nt)) - Ya
        np.savetxt(os.path.join(output_dir, 'Y_err.dat'), Y_err)
    if ode1ivp.dYa_dx:
        dY_dx_err = dYt_dx.numpy().reshape((nt)) - dYa_dx
        np.savetxt(os.path.join(output_dir, 'dY_dx_err.dat'), dY_dx_err)
