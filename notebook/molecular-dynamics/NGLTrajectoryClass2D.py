import numpy as np

import matplotlib.pyplot as plt
import ipywidgets as widgets
from ipywidgets import HBox, Output, VBox, Layout
from IPython.display import display
from ase import Atoms
from ase.io.trajectory import Trajectory
from sympy import *
from NGLUtilsClass import NGLWidgets
from itertools import product
from scipy.spatial import Voronoi, voronoi_plot_2d
import os


class NGLTrajectory2D(NGLWidgets):
    def __init__(self, trajectory):
        super().__init__(trajectory)

        self.slider_amplitude_description = widgets.Label(
            "Oscillation amplitude", layout=self.layout_description
        )
        self.slider_amplitude = widgets.FloatSlider(
            value=0.06,
            min=0.01,
            max=0.12,
            step=0.01,
            continuous_update=False,
            layout=self.layout,
        )
        self.slider_amplitude.observe(self.recompute_traj, "value")

        self.slider_C1 = widgets.FloatSlider(
            value=2, min=1, max=5, step=0.1, continuous_update=False, layout=self.layout
        )
        self.slider_C1_description = widgets.HTMLMath(
            r"$C_1$", layout=Layout(width="50px")
        )

        self.slider_C2 = widgets.FloatSlider(
            value=1, min=0, max=2, step=0.1, continuous_update=False, layout=self.layout
        )
        self.slider_C2_description = widgets.HTMLMath(
            r"$C_2$", layout=Layout(width="50px")
        )

        self.slider_C1_honey = widgets.FloatSlider(
            value=3, min=2, max=5, step=0.1, continuous_update=False, layout=self.layout
        )
        self.slider_C1_description_honey = widgets.HTMLMath(
            r"$C_1$", layout=Layout(width="50px")
        )

        self.slider_C2_honey = widgets.FloatSlider(
            value=2, min=0, max=2, step=0.1, continuous_update=False, layout=self.layout
        )
        self.slider_C2_description_honey = widgets.HTMLMath(
            r"$C_2$", layout=Layout(width="50px")
        )

        self.slider_C3_honey = widgets.FloatSlider(
            value=1, min=0, max=1, step=0.1, continuous_update=False, layout=self.layout
        )
        self.slider_C3_description_honey = widgets.HTMLMath(
            r"$C_3$", layout=Layout(width="50px")
        )

        self.slider_C1.observe(self.on_force_change, "value")
        self.slider_C2.observe(self.on_force_change, "value")
        self.slider_C1_honey.observe(self.on_force_change, "value")
        self.slider_C2_honey.observe(self.on_force_change, "value")
        self.slider_C3_honey.observe(self.on_force_change, "value")

        self.button_longitudinal = widgets.RadioButtons(
            options=["longitudinal", "transverse"], value="longitudinal"
        )
        self.button_longitudinal_description = widgets.HTMLMath(
            r"Wave direction", layout=self.layout_description
        )
        self.button_longitudinal.observe(self.on_vibration_change, "value")

        self.button_lattice = widgets.RadioButtons(
            options=["square", "honeycomb"], value="square"
        )
        self.button_lattice_description = widgets.HTMLMath(
            r"Lattice", layout=self.layout_description
        )
        self.button_lattice.observe(self.on_lattice_change, "value")

        self.button_optic = widgets.RadioButtons(
            options=["acoustic", "optical"],
            value="acoustic",
            disabled=False,
        )
        self.button_optic_description = widgets.HTMLMath(
            r"Wave type", layout=self.layout_description
        )
        self.button_optic.observe(self.on_band_change_honey, "value")

        self.output_plots = widgets.Output()
        self.output_view = widgets.Output()
        self.output_branch = widgets.Output()
        self.output_force_constants = Output()

        self.kx_array = np.linspace(-1.5 * np.pi, 1.5 * np.pi, 61)
        self.ky_array = np.linspace(-1.5 * np.pi, 1.5 * np.pi, 61)
        self.KX, self.KY = np.meshgrid(self.kx_array, self.ky_array)
        # Center of Brillouin zone
        self.idx_x = 30
        self.idx_y = 30

        self.kx_array_honey = np.linspace(-1.5 * 2 * np.pi / 3, 1.5 * 2 * np.pi / 3, 61)
        self.ky_array_honey = np.linspace(
            -1.5 * 4 * np.pi / (3 * np.sqrt(3)), 1.5 * 4 * np.pi / (3 * np.sqrt(3)), 61
        )

        self.KX_honey, self.KY_honey = np.meshgrid(
            self.kx_array_honey, self.ky_array_honey
        )
        self.idx_x_honey = 30
        self.idx_y_honey = 30

        self.init_delay = 20
        self.nframes = 51

    def addArrows(self, *args):
        self.removeArrows()

        positions = list(self.traj[0].get_positions().flatten())

        n_atoms = int(len(positions) / 3)
        color = n_atoms * [0, 1, 0]
        radius = n_atoms * [0.1]
        self.view._js(
            f"""
        var shape = new NGL.Shape("my_shape")

        var arrowBuffer = new NGL.ArrowBuffer({{position1: new Float32Array({positions}),
        position2: new Float32Array({positions}),
        color: new Float32Array({color}),
        radius: new Float32Array({radius})
        }})

        shape.addBuffer(arrowBuffer)
        globalThis.arrowBuffer = arrowBuffer;
        var shapeComp = this.stage.addComponentFromObject(shape)
        shapeComp.addRepresentation("buffer")
        shapeComp.autoView()
        """
        )
        # Remove observe callable to avoid visual glitch
        if self.handler:
            self.view.unobserve(self.handler.pop(), names=["frame"])

        def on_frame_change(change):
            frame = change["new"]

            positions = self.traj[frame].get_positions()
            positions2 = (
                positions
                + self.steps[:, :, :, frame].reshape(-1, 3)
                * self.slider_amp_arrow.value
                * 5
            )
            positions = list(positions.flatten())
            positions2 = list(positions2.flatten())
            n_atoms = int(len(positions) / 3)
            radius = n_atoms * [0.1]

            if self.tick_box_arrows.value:
                radius = n_atoms * [self.slider_arrow_radius.value]
                self.view._js(
                    f"""
                globalThis.arrowBuffer.setAttributes({{
                position1: new Float32Array({positions}),
                position2: new Float32Array({positions2}),
                radius: new Float32Array({radius})
                }})
                
                this.stage.viewer.requestRender()
                """
                )
            else:
                radius = n_atoms * [0.0]
                self.view._js(
                    f"""
                globalThis.arrowBuffer.setAttributes({{
                position1: new Float32Array({positions}),
                position2: new Float32Array({positions}),
                radius: new Float32Array({radius})
                }})

                this.stage.viewer.requestRender()
                """
                )

        self.view.observe(on_frame_change, names=["frame"])
        self.handler.append(on_frame_change)

    ######################################################################################
    ### SQUARE LATTICE
    ######################################################################################
    def compute_dispersion(self, *args):
        """
        Initialize dispersion matrix
        """
        a = Symbol("a")
        kx, ky = symbols("k_x k_y")
        K = Matrix([[kx], [ky]])
        ux, uy = symbols("u_x u_y")
        u = Matrix([[ux], [uy]])
        M, C1, C2 = symbols("M C1 C2")
        x = Matrix([[1], [0]])
        y = Matrix([[0], [1]])
        atom_positions_frst_neigh = Matrix([[1, 0], [-1, 0], [0, 1], [0, -1]])
        atom_positions_scnd_neigh = Matrix([[1, 1], [1, -1], [-1, 1], [-1, -1]])
        RHS1 = 0 * a
        RHS2 = 0 * a

        for i in range(atom_positions_frst_neigh.rows):
            position = atom_positions_frst_neigh.row(i).T
            vec = position / position.norm()
            RHS1 += (
                C1 * ((exp(I * (K.T.dot(position))) - 1) * (u.T @ vec) * (vec.T @ x))[0]
            )
            RHS2 += (
                C1 * ((exp(I * (K.T.dot(position))) - 1) * (u.T @ vec) * (vec.T @ y))[0]
            )

        for i in range(atom_positions_scnd_neigh.rows):
            position = atom_positions_scnd_neigh.row(i).T
            vec = position / position.norm()
            RHS1 += (
                C2 * ((exp(I * (K.T.dot(position))) - 1) * (u.T @ vec) * (vec.T @ x))[0]
            )
            RHS2 += (
                C2 * ((exp(I * (K.T.dot(position))) - 1) * (u.T @ vec) * (vec.T @ y))[0]
            )

        RHS1 /= -M
        RHS2 /= -M

        RHS1 = RHS1.rewrite(cos).simplify().trigsimp()
        RHS2 = RHS2.rewrite(cos).simplify().trigsimp()

        matrix = linear_eq_to_matrix([RHS1, RHS2], [ux, uy])[0]
        self.numpy_matrix = lambdify((kx, ky, C1, C2), matrix.subs({M: 1, a: 1}))

        self.compute_w_A()

    def compute_w_A(self, *args):
        """
        Computes a grid of w and A values
        """
        self.w_trans = np.zeros((61, 61), dtype="complex128")
        self.w_long = np.zeros((61, 61), dtype="complex128")
        self.A_trans = np.zeros((61, 61, 2), dtype="complex128")
        self.A_long = np.zeros((61, 61, 2), dtype="complex128")

        for i in range(61):
            for j in range(61):
                matrice = self.numpy_matrix(
                    self.kx_array[i],
                    self.ky_array[j],
                    self.slider_C1.value,
                    self.slider_C2.value,
                )
                w1, w2 = np.sqrt(np.linalg.eig(matrice)[0])
                v1, v2 = np.linalg.eig(matrice)[1].T
                idx_order = np.argsort((w1, w2))  # Sorts from smallest to largest
                w1, w2 = np.array([w1, w2])[idx_order]
                v1, v2 = np.array([v1, v2])[idx_order]

                self.w_trans[i][j] += w1
                self.A_trans[i][j] += v1
                self.w_long[i][j] += w2
                self.A_long[i][j] += v2

    def compute_trajectory_2D(self, *args):
        """
        Computes the trajectory given kx and ky
        """
        self.kx = self.kx_array[self.idx_x]
        self.ky = self.ky_array[self.idx_y]

        if self.button_longitudinal.value == "longitudinal":
            self.w = self.w_long[self.idx_x][self.idx_y]
            self.A = self.A_long[self.idx_x][self.idx_y]
        else:  # Transverse
            self.w = self.w_trans[self.idx_x][self.idx_y]
            self.A = self.A_trans[self.idx_x][self.idx_y]

        ax = np.array([1, 0, 0])
        ay = np.array([0, 1, 0])

        K = np.array([self.kx, self.ky])

        traj = Trajectory(os.path.join(self.tmp_dir.name, "atoms_2d.traj"), "w")

        self.steps = np.zeros((10, 10, 3, self.nframes))
        for frame in np.linspace(0, 50, self.nframes):
            atom_positions = []
            if self.w != 0:
                t = 2 * np.pi / self.nframes / self.w * frame
            else:
                t = 0
            for i, j in product(range(0, 10), range(0, 10)):
                vec = np.array([[i], [j]])
                step = np.real(
                    self.A
                    * self.slider_amplitude.value
                    * np.exp(1j * (K @ vec - self.w * t))
                )

                step = np.append(step, 0)  # Add z coord
                atom_positions_ = (
                    -2.5 * ax + i * ax * 0.5 - 2.5 * ay + j * ay * 0.5 + step
                )
                self.steps[i, j, :, int(frame)] += step

                atom_positions.append(atom_positions_)

            atoms = Atoms(100 * "C", positions=atom_positions)
            traj.write(atoms)

        self.replace_trajectory(
            traj=Trajectory(os.path.join(self.tmp_dir.name, "atoms_2d.traj")),
            representation="spacefill",
        )

    def initialize_2D_band_plot(self):
        """
        Initialize the 2D plot parameters
        """
        plt.ioff()
        self.fig, self.ax = plt.subplots(figsize=(4, 4))

        self.ax.set_xlim((-1.5 * np.pi, 1.5 * np.pi))
        self.ax.set_ylim((-1.5 * np.pi, 1.5 * np.pi))

        self.fig.canvas.toolbar_visible = False
        self.fig.canvas.header_visible = False
        self.fig.canvas.footer_visible = False
        self.fig.set_tight_layout(tight=True)

        # Diagonals
        self.ax.plot(
            [0, 1],
            [0, 1],
            transform=self.ax.transAxes,
            linestyle="--",
            c="black",
            linewidth=0.5,
        )
        self.ax.plot(
            [0, 1],
            [1, 0],
            transform=self.ax.transAxes,
            linestyle="--",
            c="black",
            linewidth=0.5,
        )
        # Paths
        self.ax.plot([0, np.pi], [0, np.pi], "--", c="#1EA896", linewidth=2.5)
        self.ax.plot([np.pi, np.pi], [np.pi, 0], "--", c="#FF0035", linewidth=2.5)
        self.ax.plot([np.pi, 0], [0, 0], "--", c="#A11692", linewidth=2.5)
        # First Brillouin zone
        self.ax.plot([-np.pi, np.pi], [-np.pi, -np.pi], "k", linewidth=2)
        self.ax.plot([-np.pi, np.pi], [np.pi, np.pi], "k", linewidth=2)
        self.ax.plot([np.pi, np.pi], [-np.pi, 0], "k", linewidth=2)
        self.ax.plot([-np.pi, -np.pi], [-np.pi, np.pi], "k", linewidth=2)

        self.ax.axvline(0, linestyle="--", c="black", linewidth=0.5)
        self.ax.axhline(0, linestyle="--", c="black", linewidth=0.5)
        self.ax.text(-0.4, -0.5, "$\mathbf{\Gamma}$", fontsize=16)
        self.ax.plot(0, 0, "r.")
        self.ax.text(np.pi - 0.5, -0.5, "$\mathbf{X}$", fontsize=16)
        self.ax.plot(np.pi, 0, "r.")
        self.ax.text(np.pi - 0.8, np.pi - 0.5, "$\mathbf{M}$", fontsize=16)
        self.ax.plot(np.pi, np.pi, "r.")
        self.ax.set_xlabel("k$_x$")
        self.ax.set_ylabel("k$_y$")
        self.ax.set_xticks(np.linspace(-np.pi, np.pi, 5))
        self.ax.set_xticklabels(["$-\pi/a$", "", "0", "", "$\pi/a$"])
        self.ax.set_yticks(np.linspace(-np.pi, np.pi, 5))
        self.ax.set_yticklabels(["$-\pi/a$", "", "0", "", "$\pi/a$"])

        (self.point,) = self.ax.plot([0], [0], ".", c="crimson", markersize=10)

        self.fig.canvas.mpl_connect("button_press_event", self.onclick)
        plt.ion()

    def initialize_paths_bands(self):
        """
        Initialize the dispersion curve plot parameters
        """
        plt.ioff()

        self.compute_k_w_path()

        self.fig_, self.ax_ = plt.subplots(figsize=(4, 4))
        self.fig_.canvas.toolbar_visible = False
        self.fig_.canvas.header_visible = False
        self.fig_.canvas.footer_visible = False
        self.fig_.set_tight_layout(tight=True)

        (self.line_GM_trans,) = self.ax_.plot(
            np.linspace(0, 20, 21, dtype="int32"), self.w_GM_trans, c="#1EA896"
        )
        (self.line_MX_trans,) = self.ax_.plot(
            np.linspace(20, 40, 21, dtype="int32"), self.w_MX_trans, c="#FF0035"
        )
        (self.line_XG_trans,) = self.ax_.plot(
            np.linspace(40, 60, 21, dtype="int32"), self.w_XG_trans, c="#A11692"
        )

        (self.line_GM_long,) = self.ax_.plot(
            np.linspace(0, 20, 21, dtype="int32"), self.w_GM_long, c="#1EA896"
        )
        (self.line_MX_long,) = self.ax_.plot(
            np.linspace(20, 40, 21, dtype="int32"), self.w_MX_long, c="#FF0035"
        )
        (self.line_XG_long,) = self.ax_.plot(
            np.linspace(40, 60, 21, dtype="int32"), self.w_XG_long, c="#A11692"
        )

        self.ax_.plot([20, 20], [0, 10000], "k--")
        self.ax_.plot([40, 40], [0, 10000], "k--")

        (self.point_,) = self.ax_.plot([], [], "r.", markersize=10)
        self.ax_.set_xticks([0, 20, 40, 60])
        self.ax_.set_xticklabels(
            ["$\mathbf{\Gamma}$", "$\mathbf{M}$", "$\mathbf{X}$", "$\mathbf{\Gamma}$"]
        )
        self.ax_.set_ylim(0, self.w_XG_long[0] + 1e-1)
        self.ax_.set_yticks([])
        self.ax_.set_ylabel("$\mathbf{\omega}$")

        self.fig_.canvas.mpl_connect("button_press_event", self.onclick_)
        plt.ion()

    def onclick(self, event):
        """
        Get the corresponding k values from the 2D plot
        If click is along a path, plots the point on the dispersion curve
        """
        self.x = event.xdata
        self.y = event.ydata

        # Return idx of closest element in array
        self.idx_x = (np.abs(self.kx_array - self.x)).argmin()
        self.idx_y = (np.abs(self.ky_array - self.y)).argmin()

        kx = self.kx_array[self.idx_x]
        ky = self.ky_array[self.idx_y]
        # Check if point is on plotted path
        if np.any(np.all([kx, ky] == np.c_[self.kx_GM, self.ky_GM], axis=1)):
            idx = np.where(np.all([kx, ky] == np.c_[self.kx_GM, self.ky_GM], axis=1))[
                0
            ][0]
            if self.button_longitudinal.value == "longitudinal":
                self.point_.set_data((idx, self.w_long[self.idx_x][self.idx_y]))
            else:
                self.point_.set_data((idx, self.w_trans[self.idx_x][self.idx_y]))

        elif np.any(np.all([kx, ky] == np.c_[self.kx_MX, self.ky_MX], axis=1)):
            idx = np.where(np.all([kx, ky] == np.c_[self.kx_MX, self.ky_MX], axis=1))[
                0
            ][0]
            idx += 20
            if self.button_longitudinal.value == "longitudinal":
                self.point_.set_data((idx, self.w_long[self.idx_x][self.idx_y]))
            else:
                self.point_.set_data((idx, self.w_trans[self.idx_x][self.idx_y]))

        elif np.any(np.all([kx, ky] == np.c_[self.kx_XG, self.ky_XG], axis=1)):
            idx = np.where(np.all([kx, ky] == np.c_[self.kx_XG, self.ky_XG], axis=1))[
                0
            ][0]
            idx += 40
            if self.button_longitudinal.value == "longitudinal":
                self.point_.set_data((idx, self.w_long[self.idx_x][self.idx_y]))
            else:
                self.point_.set_data((idx, self.w_trans[self.idx_x][self.idx_y]))
        else:  # Point is not on path
            self.point_.set_data([], [])

        # Update point position
        self.point.set_data(kx, ky)
        self.compute_trajectory_2D()

    def onclick_(self, event):
        """
        Get the corresponding lattice vibration closest to click
        Update the point also on the 2D plot
        """
        x = event.xdata
        y = event.ydata

        # (30,30) is center point
        if x < 20:
            idx = round(x)
            self.idx_x = 30 + idx
            self.idx_y = 30 + idx

            if np.abs(y - self.w_GM_long[idx]) < np.abs(y - self.w_GM_trans[idx]):
                self.button_longitudinal.value = "longitudinal"
                y_point = self.w_GM_long[idx]
            else:
                self.button_longitudinal.value = "transverse"
                y_point = self.w_GM_trans[idx]

        elif 20 <= x < 40:
            idx = round(x) - 20
            self.idx_x = 50
            self.idx_y = 50 - idx

            if np.abs(y - self.w_MX_long[idx]) < np.abs(y - self.w_MX_trans[idx]):
                self.button_longitudinal.value = "longitudinal"
                y_point = self.w_MX_long[idx]
            else:
                self.button_longitudinal.value = "transverse"
                y_point = self.w_MX_trans[idx]

        elif x >= 40:
            idx = round(x) - 40
            self.idx_x = 50 - idx
            self.idx_y = 30

            if np.abs(y - self.w_XG_long[idx]) < np.abs(y - self.w_XG_trans[idx]):
                self.button_longitudinal.value = "longitudinal"
                y_point = self.w_XG_long[idx]

            else:
                self.button_longitudinal.value = "transverse"
                y_point = self.w_XG_trans[idx]

        self.point_.set_data((round(x), y_point))
        self.point.set_data((self.kx_array[self.idx_x], self.ky_array[self.idx_y]))

        self.compute_trajectory_2D()

    def compute_k_w_path(self, *args):
        """
        Computes the k points and corresponding frequency along the different paths
        """
        self.w_GM_trans = np.diag(self.w_trans[30:51, 30:51])
        self.w_MX_trans = self.w_trans[50, 50:29:-1]
        self.w_XG_trans = self.w_trans[50:29:-1, 30]

        self.w_GM_long = np.diag(self.w_long[30:51, 30:51])
        self.w_MX_long = self.w_long[50, 50:29:-1]
        self.w_XG_long = self.w_long[50:29:-1, 30]

        self.kx_GM = self.kx_array[30:51]
        self.kx_MX = self.kx_array[50] * np.ones(21)
        self.kx_XG = self.kx_array[50:29:-1]
        self.ky_GM = self.ky_array[30:51]
        self.ky_MX = self.ky_array[50:29:-1]
        self.ky_XG = self.ky_array[30] * np.ones(21)

    ######################################################################################
    ### HONEYCOMB LATTICE
    ######################################################################################

    def compute_dispersion_honey(self, *args):
        """
        Initialize dispersion matrix
        """
        M, C1, C2, C3 = symbols("M C1 C2 C3")

        kx, ky = symbols("kx ky")
        k = Matrix([kx, ky])

        ux, uy = symbols("u_x u_y")
        u = Matrix([[ux], [uy]])
        vx, vy = symbols("v_x v_y")
        v = Matrix([[vx], [vy]])

        x = Matrix([[1], [0]])
        y = Matrix([[0], [1]])

        RHS1x = 0
        RHS1y = 0
        RHS2x = 0
        RHS2y = 0

        atom_positions_frst_neigh_1 = Matrix(
            [[-1, 0], [1 / 2, -sqrt(3) / 2], [1 / 2, sqrt(3) / 2]]
        )
        atom_positions_scnd_neigh_1 = Matrix(
            [
                [3 / 2, sqrt(3) / 2],
                [-3 / 2, sqrt(3) / 2],
                [-3 / 2, -sqrt(3) / 2],
                [3 / 2, -sqrt(3) / 2],
                [0, sqrt(3)],
                [0, -sqrt(3)],
            ]
        )
        atom_positions_thrd_neigh_1 = Matrix([[-1, sqrt(3)], [-1, -sqrt(3)], [2, 0]])

        atom_positions_frst_neigh_2 = Matrix(
            [[1, 0], [-1 / 2, -sqrt(3) / 2], [-1 / 2, sqrt(3) / 2]]
        )
        atom_positions_scnd_neigh_2 = Matrix(
            [
                [3 / 2, sqrt(3) / 2],
                [-3 / 2, sqrt(3) / 2],
                [-3 / 2, -sqrt(3) / 2],
                [3 / 2, -sqrt(3) / 2],
                [0, sqrt(3)],
                [0, -sqrt(3)],
            ]
        )
        atom_positions_thrd_neigh_2 = Matrix([[1, sqrt(3)], [1, -sqrt(3)], [-2, 0]])

        for i in range(atom_positions_frst_neigh_1.rows):
            position = atom_positions_frst_neigh_1.row(i).T
            vec = position / position.norm()
            RHS1x += (
                C1 * ((exp(I * (k.T.dot(position))) * v - u).T @ vec * (vec.T @ x))[0]
            )
            RHS1y += (
                C1 * ((exp(I * (k.T.dot(position))) * v - u).T @ vec * (vec.T @ y))[0]
            )

        for i in range(atom_positions_scnd_neigh_1.rows):
            position = atom_positions_scnd_neigh_1.row(i).T
            vec = position / position.norm()
            RHS1x += (
                C2 * ((exp(I * (k.T.dot(position))) * u - u).T @ vec * (vec.T @ x))[0]
            )
            RHS1y += (
                C2 * ((exp(I * (k.T.dot(position))) * u - u).T @ vec * (vec.T @ y))[0]
            )

        for i in range(atom_positions_thrd_neigh_1.rows):
            position = atom_positions_thrd_neigh_1.row(i).T
            vec = position / position.norm()
            RHS1x += (
                C3 * ((exp(I * (k.T.dot(position))) * v - u).T @ vec * (vec.T @ x))[0]
            )
            RHS1y += (
                C3 * ((exp(I * (k.T.dot(position))) * v - u).T @ vec * (vec.T @ y))[0]
            )

        for i in range(atom_positions_frst_neigh_2.rows):
            position = atom_positions_frst_neigh_2.row(i).T
            vec = position / position.norm()
            RHS2x += (
                C1 * ((exp(I * (k.T.dot(position))) * u - v).T @ vec * (vec.T @ x))[0]
            )
            RHS2y += (
                C1 * ((exp(I * (k.T.dot(position))) * u - v).T @ vec * (vec.T @ y))[0]
            )

        for i in range(atom_positions_scnd_neigh_2.rows):
            position = atom_positions_scnd_neigh_2.row(i).T
            vec = position / position.norm()
            RHS2x += (
                C2 * ((exp(I * (k.T.dot(position))) * v - v).T @ vec * (vec.T @ x))[0]
            )
            RHS2y += (
                C2 * ((exp(I * (k.T.dot(position))) * v - v).T @ vec * (vec.T @ y))[0]
            )

        for i in range(atom_positions_thrd_neigh_2.rows):
            position = atom_positions_thrd_neigh_2.row(i).T
            vec = position / position.norm()
            RHS2x += (
                C3 * ((exp(I * (k.T.dot(position))) * u - v).T @ vec * (vec.T @ x))[0]
            )
            RHS2y += (
                C3 * ((exp(I * (k.T.dot(position))) * u - v).T @ vec * (vec.T @ y))[0]
            )

        RHS1x /= -M
        RHS1y /= -M
        RHS2x /= -M
        RHS2y /= -M

        matrix = linear_eq_to_matrix([RHS1x, RHS1y, RHS2x, RHS2y], [ux, uy, vx, vy])[0]
        self.numpy_matrix_honey = lambdify((kx, ky, C1, C2, C3), matrix.subs({M: 1}))

        self.compute_w_A_honey()

    def compute_w_A_honey(self, *args):
        """
        Computes a grid of w and A values
        """
        self.w_acc_trans = np.zeros((61, 61), dtype="complex128")
        self.w_acc_long = np.zeros((61, 61), dtype="complex128")
        self.w_opt_trans = np.zeros((61, 61), dtype="complex128")
        self.w_opt_long = np.zeros((61, 61), dtype="complex128")
        self.A_acc_trans = np.zeros((61, 61, 4), dtype="complex128")
        self.A_acc_long = np.zeros((61, 61, 4), dtype="complex128")
        self.A_opt_trans = np.zeros((61, 61, 4), dtype="complex128")
        self.A_opt_long = np.zeros((61, 61, 4), dtype="complex128")

        for i in range(61):
            for j in range(61):
                matrice = self.numpy_matrix_honey(
                    self.kx_array_honey[i],
                    self.ky_array_honey[j],
                    self.slider_C1_honey.value,
                    self.slider_C2_honey.value,
                    self.slider_C3_honey.value,
                )

                # BUG: Something is wrong with applitudes :(
                w1, w2, w3, w4 = np.sqrt(np.linalg.eig(matrice)[0])
                v1, v2, v3, v4 = np.linalg.eig(matrice.astype("float64"))[1].T

                # v1, v2, v3, v4 = np.linalg.eigh(matrice)[1].T
                # v1 = np.abs(v1) * np.sign(v1)
                # v2 = np.abs(v2) * np.sign(v2)
                # v3 = np.abs(v3) * np.sign(v3)
                # v4 = np.abs(v4) * np.sign(v4)

                idx_order = np.argsort(
                    (w1, w2, w3, w4)
                )  # Sorts from smallest to largest
                w1, w2, w3, w4 = np.array([w1, w2, w3, w4])[idx_order]
                v1, v2, v3, v4 = np.array([v1, v2, v3, v4])[idx_order]

                self.w_acc_trans[i][j] = w1
                self.w_acc_long[i][j] = w2
                self.w_opt_trans[i][j] = w3
                self.w_opt_long[i][j] = w4
                self.A_acc_trans[i][j] = v1
                self.A_acc_long[i][j] = v2
                self.A_opt_trans[i][j] = v3
                self.A_opt_long[i][j] = v4

    def compute_trajectory_2D_honey(self, *args):
        """
        Computes the trajectory given kx and ky
        """
        self.kx_honey = self.kx_array_honey[self.idx_x_honey]
        self.ky_honey = self.ky_array_honey[self.idx_y_honey]

        if self.button_optic.value == "optical":
            if self.button_longitudinal.value == "longitudinal":
                self.w_honey = self.w_opt_long[self.idx_x_honey][self.idx_y_honey]
                ux, uy, vx, vy = self.A_opt_long[self.idx_x_honey][self.idx_y_honey]
            else:
                self.w_honey = self.w_opt_trans[self.idx_x_honey][self.idx_y_honey]
                ux, uy, vx, vy = self.A_opt_trans[self.idx_x_honey][self.idx_y_honey]

        elif self.button_optic.value == "acoustic":
            if self.button_longitudinal.value == "longitudinal":
                self.w_honey = self.w_acc_long[self.idx_x_honey][self.idx_y_honey]
                ux, uy, vx, vy = self.A_acc_long[self.idx_x_honey][self.idx_y_honey]
            else:
                self.w_honey = self.w_acc_trans[self.idx_x_honey][self.idx_y_honey]
                ux, uy, vx, vy = self.A_acc_trans[self.idx_x_honey][
                    self.idx_y_honey
                ]  # ux,vx,uy,vy

        ax = np.array([3 / 2, np.sqrt(3) / 2])
        ay = np.array([3 / 2, -np.sqrt(3) / 2])

        u = np.array([ux, uy])
        v = np.array([vx, vy])

        k = np.array([self.kx_honey, self.ky_honey])

        traj = Trajectory(
            os.path.join(self.tmp_dir.name, "atoms_2d_honeycomb.traj"), "w"
        )

        self.steps = np.zeros((10, 5, 3, self.nframes))

        for frame in np.linspace(0, 50, self.nframes):
            atom_positions = []
            t = 2 * np.pi / self.nframes / self.w_honey * frame
            for i, j in product(range(-2, 3), range(-2, 3)):
                vec = i * ax + j * ay
                step_1 = np.real(
                    u
                    * 5
                    * self.slider_amplitude.value
                    * np.exp(1j * (k @ vec.T - self.w_honey * t))
                )
                step_1 = np.append(step_1, 0)  # Add z-coord
                vec = np.append(vec, 0)
                atom_positions_1 = vec + np.array([1 / 2, 0, 0]) + step_1
                self.steps[i + 2, j + 2, :, int(frame)] += step_1
                atom_positions.append(atom_positions_1)
            for i, j in product(range(-2, 3), range(-2, 3)):
                vec = i * ax + j * ay
                step_2 = np.real(
                    v
                    * 5
                    * self.slider_amplitude.value
                    * np.exp(1j * (k @ vec.T - self.w_honey * t))
                )
                step_2 = np.append(step_2, 0)  # Add z-coord
                vec = np.append(vec, 0)
                atom_positions_2 = vec + np.array([-1 / 2, 0, 0]) + step_2
                self.steps[i + 7, j + 2, :, int(frame)] += step_2
                atom_positions.append(atom_positions_2)

            atoms = Atoms(len(atom_positions) * "C", positions=atom_positions)
            traj.write(atoms)

        self.replace_trajectory(
            traj=Trajectory(os.path.join(self.tmp_dir.name, "atoms_2d_honeycomb.traj")),
            representation="spacefill",
        )
        # self.view.control.zoom(0.25)

    def initialize_2D_band_plot_honey(self):
        """
        Initialize the 2D plot parameters
        """
        plt.ioff()
        b1 = 2 * np.pi * np.array([1 / 3, 1 / np.sqrt(3)])
        b2 = 2 * np.pi * np.array([1 / 3, -1 / np.sqrt(3)])

        points = np.array([[0, 0], b1, -b1, b2, -b2, b1 + b2, -b1 - b2])
        vor = Voronoi(points)

        # Taken from vor.vertices and reorganized
        self.point_honeys_hexagon = np.array(
            [
                [-2 * np.pi / 3, -2 * np.pi / (3 * np.sqrt(3))],
                [0.0, -4 * np.pi / (3 * np.sqrt(3))],
                [2 * np.pi / 3, -2 * np.pi / (3 * np.sqrt(3))],
                [2 * np.pi / 3, 2 * np.pi / (3 * np.sqrt(3))],
                [0.0, 4 * np.pi / (3 * np.sqrt(3))],
                [-2 * np.pi / 3, 2 * np.pi / (3 * np.sqrt(3))],
            ]
        )

        self.fig_honey = voronoi_plot_2d(vor, show_points=False, show_vertices=False)
        px = 1 / plt.rcParams["figure.dpi"]
        self.fig_honey.canvas.toolbar_visible = False
        self.fig_honey.canvas.header_visible = False
        self.fig_honey.canvas.footer_visible = False
        self.fig_honey.set_tight_layout(tight=True)
        self.fig_honey.set_figheight(400 * px)
        self.fig_honey.set_figwidth(450 * px)
        (self.ax_honey,) = self.fig_honey.axes
        self.ax_honey.set_xlim((-3, 3))
        self.ax_honey.set_ylim((-3, 3))

        self.ax_honey.plot(
            [self.point_honeys_hexagon[0, 0], self.point_honeys_hexagon[3, 0]],
            [self.point_honeys_hexagon[0, 1], self.point_honeys_hexagon[3, 1]],
            "k--",
            linewidth=1,
        )
        self.ax_honey.plot(
            [self.point_honeys_hexagon[1, 0], self.point_honeys_hexagon[4, 0]],
            [self.point_honeys_hexagon[1, 1], self.point_honeys_hexagon[4, 1]],
            "k--",
            linewidth=1,
        )
        self.ax_honey.plot(
            [self.point_honeys_hexagon[2, 0], self.point_honeys_hexagon[5, 0]],
            [self.point_honeys_hexagon[2, 1], self.point_honeys_hexagon[5, 1]],
            "k--",
            linewidth=1,
        )

        self.ax_honey.plot(
            [0, self.point_honeys_hexagon[3, 0]],
            [0, self.point_honeys_hexagon[3, 1]],
            "--",
            c="#1EA896",
            linewidth=2.5,
        )
        self.ax_honey.plot(
            [self.point_honeys_hexagon[3, 0], self.point_honeys_hexagon[3, 0]],
            [self.point_honeys_hexagon[3, 1], 0],
            "--",
            c="#FF0035",
            linewidth=2.5,
        )
        self.ax_honey.plot(
            [self.point_honeys_hexagon[3, 0], 0],
            [0, 0],
            "--",
            c="#A11692",
            linewidth=2.5,
        )

        (self.point_honey,) = self.ax_honey.plot(
            [0], [0], ".", c="crimson", markersize=10
        )

        self.ax_honey.set_xlabel("k$_x$")
        self.ax_honey.set_ylabel("k$_y$")
        self.ax_honey.set_xticks(np.linspace(-2 * np.pi / 3, 2 * np.pi / 3, 5))
        self.ax_honey.set_xticklabels(
            [r"$-\frac{2\pi}{3a}$", "", "0", "", r"$\frac{2\pi}{3a}$"]
        )
        self.ax_honey.set_yticks(
            np.linspace(-4 * np.pi / 3 / np.sqrt(3), 4 * np.pi / 3 / np.sqrt(3), 5)
        )
        self.ax_honey.set_yticklabels(
            [
                r"$-\frac{4\pi}{3\sqrt{3}a}$",
                r"$-\frac{2\pi}{3\sqrt{3}a}$",
                "0",
                r"$\frac{2\pi}{3\sqrt{3}a}$",
                r"$\frac{4\pi}{3\sqrt{3}a}$",
            ]
        )

        self.ax_honey.text(-0.2, -0.5, "$\mathbf{\Gamma}$", fontsize=16)
        self.ax_honey.plot(0, 0, "r.")
        self.ax_honey.text(
            self.point_honeys_hexagon[3, 0],
            self.point_honeys_hexagon[3, 1] + 0.2,
            "$\mathbf{K}$",
            fontsize=16,
        )
        self.ax_honey.plot(
            self.point_honeys_hexagon[3, 0], self.point_honeys_hexagon[3, 1], "r."
        )
        self.ax_honey.text(
            self.point_honeys_hexagon[3, 0] + 0.02, 0 - 0.4, "$\mathbf{M}$", fontsize=16
        )
        self.ax_honey.plot(self.point_honeys_hexagon[3, 0], 0, "r.")

        self.fig_honey.canvas.mpl_connect("button_press_event", self.onclick_honey)
        plt.ion()

    def initialize_paths_bands_honey(self):
        """
        Initialize the dispersion curve plot parameters
        """
        plt.ioff()

        self.fig_honey_, self.ax_honey_ = plt.subplots(figsize=(4, 4))

        self.fig_honey_.canvas.toolbar_visible = False
        self.fig_honey_.canvas.header_visible = False
        self.fig_honey_.canvas.footer_visible = False
        self.fig_honey_.set_tight_layout(tight=True)

        self.compute_k_w_path_honey()

        self.x_GM = np.linspace(0, 10, 11)
        self.x_MK = np.linspace(10, 20, 11)
        self.x_XG = np.linspace(20, 40, 21)

        (self.line_GK_acc_long,) = self.ax_honey_.plot(
            self.x_GM, self.w_GK_acc_long, "#1EA896"
        )  # GK
        (self.line_KM_acc_long,) = self.ax_honey_.plot(
            self.x_MK, self.w_KM_acc_long, "#FF0035"
        )  # KM
        (self.line_MG_acc_long,) = self.ax_honey_.plot(
            self.x_XG, self.w_MG_acc_long, "#A11692"
        )  # MG
        (self.line_GK_opt_long,) = self.ax_honey_.plot(
            self.x_GM, self.w_GK_opt_long, "#1EA896"
        )  # GK
        (self.line_KM_opt_long,) = self.ax_honey_.plot(
            self.x_MK, self.w_KM_opt_long, "#FF0035"
        )  # KM
        (self.line_MG_opt_long,) = self.ax_honey_.plot(
            self.x_XG, self.w_MG_opt_long, "#A11692"
        )  # MG

        (self.line_GK_acc_trans,) = self.ax_honey_.plot(
            self.x_GM, self.w_GK_acc_trans, "#1EA896"
        )  # GK
        (self.line_KM_acc_trans,) = self.ax_honey_.plot(
            self.x_MK, self.w_KM_acc_trans, "#FF0035"
        )  # KM
        (self.line_MG_acc_trans,) = self.ax_honey_.plot(
            self.x_XG, self.w_MG_acc_trans, "#A11692"
        )  # MG
        (self.line_GK_opt_trans,) = self.ax_honey_.plot(
            self.x_GM, self.w_GK_opt_trans, "#1EA896"
        )  # GK
        (self.line_KM_opt_trans,) = self.ax_honey_.plot(
            self.x_MK, self.w_KM_opt_trans, "#FF0035"
        )  # KM
        (self.line_MG_opt_trans,) = self.ax_honey_.plot(
            self.x_XG, self.w_MG_opt_trans, "#A11692"
        )  # MG

        self.ax_honey_.plot([10, 10], [0, 1000], "k--")
        self.ax_honey_.plot([20, 20], [0, 1000], "k--")

        (self.point_honey_,) = self.ax_honey_.plot([], [], "r.", markersize=10)
        self.ax_honey_.set_xticks([0, 10, 20, 40])
        self.ax_honey_.set_xticklabels(
            ["$\mathbf{\Gamma}$", "$\mathbf{K}$", "$\mathbf{M}$", "$\mathbf{\Gamma}$"]
        )
        self.ax_honey_.set_ylim(0, 5 + 1e-2)

        self.ax_honey_.set_xlim(0, 40)

        self.ax_honey_.set_yticks([])
        self.ax_honey_.set_ylabel("$\mathbf{\omega}$")
        self.fig_honey_.canvas.mpl_connect("button_press_event", self.onclick_honey_)
        plt.ion()

    def onclick_honey(self, event):
        """
        Get the corresponding k values from the 2D plot
        If click is along a path, plots the point on the dispersion curve
        """
        self.x_honey = event.xdata
        self.y_honey = event.ydata

        # Return idx of closest element in array
        self.idx_x_honey = (np.abs(self.kx_array_honey - self.x_honey)).argmin()
        self.idx_y_honey = (np.abs(self.ky_array_honey - self.y_honey)).argmin()

        kx = self.kx_array_honey[self.idx_x_honey]
        ky = self.ky_array_honey[self.idx_y_honey]

        # Check if point is on plotted path
        if np.any(
            np.all(
                np.isclose([kx, ky], np.c_[self.kx_GK_honey, self.ky_GK_honey]), axis=1
            )
        ):
            idx = np.where(
                np.all(
                    np.isclose([kx, ky], np.c_[self.kx_GK_honey, self.ky_GK_honey]),
                    axis=1,
                )
            )[0][0]
            if self.button_optic.value == "acoustic":
                if self.button_longitudinal.value == "longitudinal":
                    self.point_honey_.set_data((idx, self.w_GK_acc_long[idx]))
                else:
                    self.point_honey_.set_data((idx, self.w_GK_acc_trans[idx]))
            else:
                if self.button_longitudinal.value == "longitudinal":
                    self.point_honey_.set_data((idx, self.w_GK_opt_long[idx]))
                else:
                    self.point_honey_.set_data((idx, self.w_GK_opt_trans[idx]))

        elif np.any(
            np.all(
                np.isclose([kx, ky], np.c_[self.kx_KM_honey, self.ky_KM_honey]), axis=1
            )
        ):
            idx = np.where(
                np.all(
                    np.isclose([kx, ky], np.c_[self.kx_KM_honey, self.ky_KM_honey]),
                    axis=1,
                )
            )[0][0]
            # idx+=10
            if self.button_optic.value == "acoustic":
                if self.button_longitudinal.value == "longitudinal":
                    self.point_honey_.set_data((idx + 10, self.w_KM_acc_long[idx]))
                else:
                    self.point_honey_.set_data((idx + 10, self.w_KM_acc_trans[idx]))
            else:
                if self.button_longitudinal.value == "longitudinal":
                    self.point_honey_.set_data((idx + 10, self.w_KM_opt_long[idx]))
                else:
                    self.point_honey_.set_data((idx + 10, self.w_KM_opt_trans[idx]))

        elif np.any(
            np.all(
                np.isclose([kx, ky], np.c_[self.kx_MG_honey, self.ky_MG_honey]), axis=1
            )
        ):
            idx = np.where(
                np.all(
                    np.isclose([kx, ky], np.c_[self.kx_MG_honey, self.ky_MG_honey]),
                    axis=1,
                )
            )[0][0]
            # idx+=20
            if self.button_optic.value == "acoustic":
                if self.button_longitudinal.value == "longitudinal":
                    self.point_honey_.set_data((idx + 20, self.w_MG_acc_long[idx]))
                else:
                    self.point_honey_.set_data((idx + 20, self.w_MG_acc_trans[idx]))
            else:
                if self.button_longitudinal.value == "longitudinal":
                    self.point_honey_.set_data((idx + 20, self.w_MG_opt_long[idx]))
                else:
                    self.point_honey_.set_data((idx + 20, self.w_MG_opt_trans[idx]))
        else:  # Point is not on path
            self.point_honey_.set_data([], [])
        # Update point position
        self.point_honey.set_data(kx, ky)
        self.compute_trajectory_2D_honey()

    def onclick_honey_(self, event):
        """
        Get the corresponding lattice vibration closest to click
        Update the point also on the 2D plot
        """

        self.x_honey_ = event.xdata
        self.y_honey_ = event.ydata

        # Center is (30,30)
        if self.x_honey_ < 10:
            idx = round(self.x_honey_)
            self.idx_x_honey = 30 + 2 * idx
            self.idx_y_honey = 30 + idx

            idx_band = np.argmin(
                np.abs(
                    self.y_honey_
                    - np.c_[
                        self.w_GK_acc_long[idx],
                        self.w_GK_acc_trans[idx],
                        self.w_GK_opt_long[idx],
                        self.w_GK_opt_trans[idx],
                    ]
                )
            )
            if idx_band == 0:
                self.button_optic.value = "acoustic"
                self.button_longitudinal.value = "longitudinal"
                y = self.w_GK_acc_long[idx]
            elif idx_band == 1:
                self.button_optic.value = "acoustic"
                self.button_longitudinal.value = "transverse"
                y = self.w_GK_acc_trans[idx]
            elif idx_band == 2:
                self.button_optic.value = "optical"
                self.button_longitudinal.value = "longitudinal"
                y = self.w_GK_opt_long[idx]
            elif idx_band == 3:
                self.button_optic.value = "optical"
                self.button_longitudinal.value = "transverse"
                y = self.w_GK_opt_trans[idx]

        elif 10 <= self.x_honey_ < 20:
            idx = round(self.x_honey_) - 10
            self.idx_x_honey = 50
            self.idx_y_honey = 40 - idx

            idx_band = np.argmin(
                np.abs(
                    self.y_honey_
                    - np.c_[
                        self.w_KM_acc_long[idx],
                        self.w_KM_acc_trans[idx],
                        self.w_KM_opt_long[idx],
                        self.w_KM_opt_trans[idx],
                    ]
                )
            )
            if idx_band == 0:
                self.button_optic.value = "acoustic"
                self.button_longitudinal.value = "longitudinal"
                y = self.w_KM_acc_long[idx]
            elif idx_band == 1:
                self.button_optic.value = "acoustic"
                self.button_longitudinal.value = "transverse"
                y = self.w_KM_acc_trans[idx]
            elif idx_band == 2:
                self.button_optic.value = "optical"
                self.button_longitudinal.value = "longitudinal"
                y = self.w_KM_opt_long[idx]
            elif idx_band == 3:
                self.button_optic.value = "optical"
                self.button_longitudinal.value = "transverse"
                y = self.w_KM_opt_trans[idx]

        elif self.x_honey_ >= 20:
            idx = round(self.x_honey_) - 20
            self.idx_x_honey = 50 - idx
            self.idx_y_honey = 30

            idx_band = np.argmin(
                np.abs(
                    self.y_honey_
                    - np.c_[
                        self.w_MG_acc_long[idx],
                        self.w_MG_acc_trans[idx],
                        self.w_MG_opt_long[idx],
                        self.w_MG_opt_trans[idx],
                    ]
                )
            )
            if idx_band == 0:
                self.button_optic.value = "acoustic"
                self.button_longitudinal.value = "longitudinal"
                y = self.w_MG_acc_long[idx]
            elif idx_band == 1:
                self.button_optic.value = "acoustic"
                self.button_longitudinal.value = "transverse"
                y = self.w_MG_acc_trans[idx]
            elif idx_band == 2:
                self.button_optic.value = "optical"
                self.button_longitudinal.value = "longitudinal"
                y = self.w_MG_opt_long[idx]
            elif idx_band == 3:
                self.button_optic.value = "optical"
                self.button_longitudinal.value = "transverse"
                y = self.w_MG_opt_trans[idx]

        self.point_honey_.set_data((round(self.x_honey_), y))
        self.point_honey.set_data(
            (
                self.kx_array_honey[self.idx_x_honey],
                self.ky_array_honey[self.idx_y_honey],
            )
        )

        self.compute_trajectory_2D_honey()

    def compute_k_w_path_honey(self, *args):
        """
        Computes the k points and corresponding frequency along the different paths
        """
        self.kx_GK_honey = self.kx_array_honey[30:51:2]
        self.kx_KM_honey = self.kx_array_honey[50] * np.ones(11)
        self.kx_MG_honey = self.kx_array_honey[50:29:-1]
        self.ky_GK_honey = self.ky_array_honey[30:41]
        self.ky_KM_honey = self.ky_array_honey[40:29:-1]
        self.ky_MG_honey = self.ky_array_honey[30] * np.ones(21)

        self.w_GK_acc_long = self.w_acc_long[np.arange(30, 51, 2), np.arange(30, 41)]
        self.w_KM_acc_long = self.w_acc_long[50, 40:29:-1]
        self.w_MG_acc_long = self.w_acc_long[50:29:-1, 30]

        self.w_GK_opt_long = self.w_opt_long[np.arange(30, 51, 2), np.arange(30, 41)]
        self.w_KM_opt_long = self.w_opt_long[50, 40:29:-1]
        self.w_MG_opt_long = self.w_opt_long[50:29:-1, 30]

        self.w_GK_acc_trans = self.w_acc_trans[np.arange(30, 51, 2), np.arange(30, 41)]
        self.w_KM_acc_trans = self.w_acc_trans[50, 40:29:-1]
        self.w_MG_acc_trans = self.w_acc_trans[50:29:-1, 30]

        self.w_GK_opt_trans = self.w_opt_trans[np.arange(30, 51, 2), np.arange(30, 41)]
        self.w_KM_opt_trans = self.w_opt_trans[50, 40:29:-1]
        self.w_MG_opt_trans = self.w_opt_trans[50:29:-1, 30]

    def on_band_change_honey(self, *args):
        """
        Recomputes the trajectory and moves the point accordingly
        """
        x, y = self.point_honey_.get_data()
        if self.button_longitudinal.value == "longitudinal":
            if y:
                if self.button_optic.value == "acoustic":
                    self.point_honey_.set_data(
                        (x, self.w_acc_long[self.idx_x_honey][self.idx_y_honey])
                    )
                else:
                    self.point_honey_.set_data(
                        (x, self.w_opt_long[self.idx_x_honey][self.idx_y_honey])
                    )
        else:
            if y:
                if self.button_optic.value == "acoustic":
                    self.point_honey_.set_data(
                        (x, self.w_acc_trans[self.idx_x_honey][self.idx_y_honey])
                    )
                else:
                    self.point_honey_.set_data(
                        (x, self.w_opt_trans[self.idx_x_honey][self.idx_y_honey])
                    )

        self.compute_trajectory_2D_honey()

    def on_force_change(self, *args):
        """
        Recomputes the dispersion relation and move the point accordingly
        """
        if self.button_lattice.value == "square":
            self.compute_w_A()
            self.compute_k_w_path()

            self.line_GM_trans.set_data(
                np.linspace(0, 20, 21, dtype="int32"), self.w_GM_trans
            )
            self.line_MX_trans.set_data(
                np.linspace(20, 40, 21, dtype="int32"), self.w_MX_trans
            )
            self.line_XG_trans.set_data(
                np.linspace(40, 60, 21, dtype="int32"), self.w_XG_trans
            )

            self.line_GM_long.set_data(
                np.linspace(0, 20, 21, dtype="int32"), self.w_GM_long
            )
            self.line_MX_long.set_data(
                np.linspace(20, 40, 21, dtype="int32"), self.w_MX_long
            )
            self.line_XG_long.set_data(
                np.linspace(40, 60, 21, dtype="int32"), self.w_XG_long
            )
            max_height = np.max(
                [
                    self.w_GM_long,
                    self.w_MX_long,
                    self.w_XG_long,
                    self.w_GM_trans,
                    self.w_MX_trans,
                    self.w_XG_trans,
                ]
            )
            self.ax_.set_ylim((0, max_height + 0.1 * max_height))
            x, y = self.point_.get_data()
            if y:
                if x < 20:
                    idx = round(x)
                    if self.button_longitudinal.value == "longitudinal":
                        y_point = self.w_GM_long[idx]
                    else:
                        y_point = self.w_GM_trans[idx]

                elif 20 <= x < 40:
                    idx = round(x) - 20
                    if self.button_longitudinal.value == "longitudinal":
                        y_point = self.w_MX_long[idx]
                    else:
                        y_point = self.w_MX_trans[idx]

                elif x >= 40:
                    idx = round(x) - 40
                    if self.button_longitudinal.value == "longitudinal":
                        y_point = self.w_XG_long[idx]
                    else:
                        y_point = self.w_XG_trans[idx]

                self.point_.set_data((x, y_point))

        elif self.button_lattice.value == "honeycomb":
            self.compute_w_A_honey()
            self.compute_k_w_path_honey()

            self.line_GK_acc_long.set_data((self.x_GM, self.w_GK_acc_long))
            self.line_KM_acc_long.set_data((self.x_MK, self.w_KM_acc_long))
            self.line_MG_acc_long.set_data((self.x_XG, self.w_MG_acc_long))
            self.line_GK_opt_long.set_data((self.x_GM, self.w_GK_opt_long))
            self.line_KM_opt_long.set_data((self.x_MK, self.w_KM_opt_long))
            self.line_MG_opt_long.set_data((self.x_XG, self.w_MG_opt_long))
            self.line_GK_acc_trans.set_data((self.x_GM, self.w_GK_acc_trans))
            self.line_KM_acc_trans.set_data((self.x_MK, self.w_KM_acc_trans))
            self.line_MG_acc_trans.set_data((self.x_XG, self.w_MG_acc_trans))
            self.line_GK_opt_trans.set_data((self.x_GM, self.w_GK_opt_trans))
            self.line_KM_opt_trans.set_data((self.x_MK, self.w_KM_opt_trans))
            self.line_MG_opt_trans.set_data((self.x_XG, self.w_MG_opt_trans))

            max_height = np.real(
                np.max(
                    np.r_[self.w_MG_opt_long, self.w_GK_opt_long, self.w_KM_opt_long]
                )
            )
            self.ax_honey_.set_ylim((0, max_height + 0.1 * max_height))
            x, y = self.point_honey_.get_data()
            if y:
                if x < 10:
                    idx = round(x)
                    if self.button_optic.value == "acoustic":
                        if self.button_longitudinal.value == "longitudinal":
                            y_point = self.w_GK_acc_long[idx]
                        else:
                            y_point = self.w_GK_acc_trans[idx]
                    else:
                        if self.button_longitudinal.value == "longitudinal":
                            y_point = self.w_GK_opt_long[idx]
                        else:
                            y_point = self.w_GK_opt_trans[idx]
                elif 10 <= x < 20:
                    idx = round(x) - 10
                    if self.button_optic.value == "acoustic":
                        if self.button_longitudinal.value == "longitudinal":
                            y_point = self.w_KM_acc_long[idx]
                        else:
                            y_point = self.w_KM_acc_trans[idx]
                    else:
                        if self.button_longitudinal.value == "longitudinal":
                            y_point = self.w_KM_opt_long[idx]
                        else:
                            y_point = self.w_KM_opt_trans[idx]

                elif x >= 20:
                    idx = round(x) - 20
                    if self.button_optic.value == "acoustic":
                        if self.button_longitudinal.value == "longitudinal":
                            y_point = self.w_MG_acc_long[idx]
                        else:
                            y_point = self.w_MG_acc_trans[idx]
                    else:
                        if self.button_longitudinal.value == "longitudinal":
                            y_point = self.w_MG_opt_long[idx]
                        else:
                            y_point = self.w_MG_opt_trans[idx]

                self.point_honey_.set_data((x, y_point))

    def on_vibration_change(self, *args):
        """
        Modifiy the point position on the dispersion curve
        Recomputes the corresponding trajectory
        """
        if self.button_lattice.value == "square":
            x, y = self.point_.get_data()
            if self.button_longitudinal.value == "longitudinal":
                if y:  # Check that point actually exists, data is not ([],[])
                    self.point_.set_data((x, self.w_long[self.idx_x][self.idx_y]))
            else:
                if y:
                    self.point_.set_data((x, self.w_trans[self.idx_x][self.idx_y]))

            self.compute_trajectory_2D()
        else:
            x, y = self.point_honey_.get_data()
            if self.button_longitudinal.value == "longitudinal":
                if y:
                    if self.button_optic.value == "acoustic":
                        self.point_honey_.set_data(
                            (x, self.w_acc_long[self.idx_x_honey][self.idx_y_honey])
                        )
                    else:
                        self.point_honey_.set_data(
                            (x, self.w_opt_long[self.idx_x_honey][self.idx_y_honey])
                        )
            else:
                if y:
                    if self.button_optic.value == "acoustic":
                        self.point_honey_.set_data(
                            (x, self.w_acc_trans[self.idx_x_honey][self.idx_y_honey])
                        )
                    else:
                        self.point_honey_.set_data(
                            (x, self.w_opt_trans[self.idx_x_honey][self.idx_y_honey])
                        )

            self.compute_trajectory_2D_honey()

    def on_lattice_change(self, *args):
        """
        Update the slider depending on the lattice selected
        """
        with self.output_force_constants:
            if self.button_lattice.value == "square":
                self.output_force_constants.clear_output()
                display(
                    VBox(
                        [
                            HBox([self.slider_C1_description, self.slider_C1]),
                            HBox([self.slider_C2_description, self.slider_C2]),
                        ]
                    )
                )
            elif self.button_lattice.value == "honeycomb":
                self.output_force_constants.clear_output()
                display(
                    VBox(
                        [
                            HBox(
                                [self.slider_C1_description_honey, self.slider_C1_honey]
                            ),
                            HBox(
                                [self.slider_C2_description_honey, self.slider_C2_honey]
                            ),
                            HBox(
                                [self.slider_C3_description_honey, self.slider_C3_honey]
                            ),
                        ]
                    )
                )

        with self.output_plots:
            if self.button_lattice.value == "square":
                self.output_plots.clear_output()
                display(HBox([self.fig.canvas, self.fig_.canvas]))

            elif self.button_lattice.value == "honeycomb":
                self.output_plots.clear_output()
                display(HBox([self.fig_honey.canvas, self.fig_honey_.canvas]))

        if self.button_lattice.value == "square":
            self.compute_trajectory_2D()
        elif self.button_lattice.value == "honeycomb":
            self.compute_trajectory_2D_honey()
        with self.output_branch:
            longitudinal = HBox(
                [self.button_longitudinal_description, self.button_longitudinal]
            )
            optic = HBox([self.button_optic_description, self.button_optic])
            if self.button_lattice.value == "square":
                self.output_branch.clear_output()
                display(longitudinal)
            elif self.button_lattice.value == "honeycomb":
                self.output_branch.clear_output()
                display(longitudinal, optic)

    def recompute_traj(self, *args):
        """
        Recomputes the trajectory for the right lattice
        """
        if self.button_lattice.value == "square":
            self.compute_trajectory_2D()
        elif self.button_lattice.value == "honeycomb":
            self.compute_trajectory_2D_honey()
