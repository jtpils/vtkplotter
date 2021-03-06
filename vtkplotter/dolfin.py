# FEniCS/Dolfin support API
#
from __future__ import division, print_function

import vtk
from vtk.util.numpy_support import numpy_to_vtk

import numpy as np

import vtkplotter.utils as utils
from vtkplotter.utils import printHistogram, ProgressBar, plotMatrix

import vtkplotter.docs as docs

from vtkplotter.colors import printc

import vtkplotter.settings as settings
from vtkplotter.settings import datadir, embedWindow

from vtkplotter.actors import Actor

from vtkplotter.vtkio import load, screenshot, Video, exportWindow

import vtkplotter.shapes as shapes
from vtkplotter.shapes import Text, Latex

from vtkplotter.plotter import show, clear, Plotter
from vtkplotter.plotter import closeWindow, closePlotter, interactive

__doc__ = (
    """
`FEniCS/Dolfin <https://fenicsproject.org>`_ support submodule.

Install with commands (e.g. in Anaconda3):

    .. code-block:: bash

        conda install -c conda-forge fenics
        pip install vtkplotter

Basic example:

    .. code-block:: python

        import dolfin
        from vtkplotter.dolfin import datadir, plot

        mesh = dolfin.Mesh(datadir+"dolfin_fine.xml")

        plot(mesh)

    |dolfinmesh|

Find many more examples in
`vtkplotter/examples/dolfin <https://github.com/marcomusy/vtkplotter/blob/master/examples/other/dolfin>`_


Image Gallery
=============

+-------------------------------------------------+-------------------------------------------------+
|                                                 | *(click on the figure to get to the script)*    |
+-------------------------------------------------+-------------------------------------------------+
| |ex03_poisson|                                  |   |ex02_tetralize-mesh|                         |
+-------------------------------------------------+-------------------------------------------------+
| Poisson equation with Dirichlet conditions      | Generate a tet-mesh from a polygonal surface    |
+-------------------------------------------------+-------------------------------------------------+
| |demo_submesh|                                  |   |pi_estimate|                                 |
+-------------------------------------------------+-------------------------------------------------+
| Extract submesh boundaries                      | Get pi from the integral of a circle            |
+-------------------------------------------------+-------------------------------------------------+
| |ex06_elasticity1|                              |   |ex06_elasticity2|                            |
+-------------------------------------------------+-------------------------------------------------+
| Solve a hyperelasticity problem...              | ...with different types of visulizations.       |
+-------------------------------------------------+-------------------------------------------------+
| |ft04_heat_gaussian|                            |   |demo_cahn-hilliard|                          |
+-------------------------------------------------+-------------------------------------------------+
| Diffusion of a Gaussian hill                    | Solve the Cahn-Hilliard equation                |
+-------------------------------------------------+-------------------------------------------------+
| |navier-stokes_lshape|                          |   |stokes1|                                     |
+-------------------------------------------------+-------------------------------------------------+
| The Navier-Stokes equations on L-shaped domain  | Stokes equations with Taylor-Hood elements      |
+-------------------------------------------------+-------------------------------------------------+
| |elastodynamics|                                |   |ft02_poisson_membrane|                       |
+-------------------------------------------------+-------------------------------------------------+
| Time-integration of the elastodynamics equation | Deflection of a membrane under a point load     |
+-------------------------------------------------+-------------------------------------------------+
| |magnetostatics|                                |   |turing_pattern|                              |
+-------------------------------------------------+-------------------------------------------------+
| Magnetic field of a solenoid                    | Patterns of Turing type reaction-diffusion      |
+-------------------------------------------------+-------------------------------------------------+
| |scalemesh|                                     |   |heatconv|                                    |
+-------------------------------------------------+-------------------------------------------------+
| Scale and elevate a mesh along one coordinate   | Heat equation in a moving media                 |
+-------------------------------------------------+-------------------------------------------------+
| |elasticbeam|                                   |   |wavy_1d|                                     |
+-------------------------------------------------+-------------------------------------------------+
| A soft beam deforming under its own weight      | The 1D wave eq. with the Crank Nicolson method  |
+-------------------------------------------------+-------------------------------------------------+
| |customAxes|                                    | |awefem|                                        |
+-------------------------------------------------+-------------------------------------------------+
| Customizing axes style and appearence           |The wave equation in arbitrary nr. of dimensions |
+-------------------------------------------------+-------------------------------------------------+

|fenics_logo|
"""
    + docs._defs
)

__all__ = [
    "plot",
    "MeshActor",
    "MeshPoints",
    "MeshLines",
    "MeshArrows",
    "load",
    "show",
    "clear",
    "printc",
    "printHistogram",
    "Plotter",
    "ProgressBar",
    "Text",
    "Latex",
    "datadir",
    "screenshot",
    "Video",
    "plotMatrix",
    "exportWindow",
    "closeWindow",
    "closePlotter",
    "interactive",
    "embedWindow",
]


def _inputsort(obj):
    import dolfin

    u = None
    mesh = None
    if not utils.isSequence(obj):
        obj = [obj]

    for ob in obj:
        inputtype = str(type(ob))
        #printc('inputtype is', inputtype, c=2)

        if "vtk" in inputtype: # skip vtk objects, will be added later
            continue

        if "dolfin" in inputtype:
            if "MeshFunction" in inputtype:
                mesh = ob.mesh()

                if ob.dim()>0:
                    printc('MeshFunction of dim>0 not supported.', c=1)
                    printc('Try e.g.:  MeshFunction("size_t", mesh, 0)', c=1, italic=1)
                    printc('instead of MeshFunction("size_t", mesh, 1)', c=1, strike=1)
                else:
                    #printc(ob.dim(), mesh.num_cells(), len(mesh.coordinates()), len(ob.array()))
                    V = dolfin.FunctionSpace(mesh, "CG", 1)
                    u = dolfin.Function(V)
                    v2d = dolfin.vertex_to_dof_map(V)
                    u.vector()[v2d] = ob.array()
            elif "Function" in inputtype or "Expression" in inputtype:
                u = ob
            elif "Mesh" in inputtype:
                mesh = ob

        if "str" in inputtype:
            mesh = dolfin.Mesh(ob)

    if u and not mesh and hasattr(u, "function_space"):
        V = u.function_space()
        if V:
            mesh = V.mesh()
    if u and not mesh and hasattr(u, "mesh"):
        mesh = u.mesh()

    #printc('------------------------------------')
    #printc('mesh.topology dim=', mesh.topology().dim())
    #printc('mesh.geometry dim=', mesh.geometry().dim())
    #if u: printc('u.value_rank()', u.value_rank())
    return (mesh, u)



def plot(*inputobj, **options):
    """
    Plot the object(s) provided.

    Input can be: ``vtkActor``, ``vtkVolume``, ``dolfin.Mesh``, ``dolfin.MeshFunction*``,
    ``dolfin.Expression`` or ``dolfin.Function``.

    :return: the current ``Plotter`` class instance.

    :param str mode: one or more of the following can be combined in any order

        - `mesh`/`color`, will plot the mesh, by default colored with a scalar if available

            - `warp`, mesh will be modified by a displacement function
            - `contour`, to be implemented
        - `arrows`, mesh displacements are plotted as scaled arrows.
        - `lines`, mesh displacements are plotted as scaled lines.
        - `tensors`, to be implemented

    :param bool add: add the input objects without clearing the already plotted ones
    :param float density: show only a subset of lines or arrows [0-1]
    :param bool wire[frame]: visualize mesh as wireframe [False]
    :param c[olor]: set mesh color [None]
    :param bool exterior: only show the outer surface of the mesh [False]
    :param float alpha: set object's transparency [1]
    :param float lw: line width of the mesh (set to zero to hide mesh) [0.5]
    :param float ps: set point size of mesh vertices [None]
    :param float z: add a constant to z-coordinate (useful to show 2D slices as function of time)
    :param str legend: add a legend to the top-right of window [None]
    :param bool scalarbar: add a scalarbar to the window ['vertical']
    :param float vmin: set the minimum for the range of the scalar [None]
    :param float vmax: set the maximum for the range of the scalar [None]
    :param float scale: add a scaling factor to arrows and lines sizes [1]
    :param str cmap: choose a color map for scalars
    :param int bands: group colors in `n` bands
    :param str shading: mesh shading ['flat', 'phong', 'gouraud']
    :param str text: add a gray text comment to the top-left of the window [None]

    :param dict isolines: dictionary of isolines properties

        - n, (int) - add this number of isolines to the mesh
        - c, - isoline color
        - lw, (float) - isoline width
        - z, (float) - add to the isoline z coordinate to make them more visible

    :param float warpZfactor: elevate z-axis by scalar value (useful for 2D geometries)
    :param float warpYfactor: elevate z-axis by scalar value (useful for 1D geometries)

    :param list scaleMeshFactors: rescale mesh by these factors [1,1,1]

    :param bool newPlotter: spawn a new instance of Plotter class, pops up a new window
    :param int at: renderer number to plot to
    :param list shape: subdvide window in (n,m) rows and columns
    :param int N: automatically subdvide window in N renderers
    :param list pos: (x,y) coordinates of the window position on screen
    :param size: window size (x,y)

    :param str title: window title
    :param bg: background color name of window
    :param bg2: second background color name to create a color gradient
    :param int style: choose a predefined style [0-4]

      - 0, `vtkplotter`, style (blackboard background, rainbow color map)
      - 1, `matplotlib`, style (white background, viridis color map)
      - 2, `paraview`, style
      - 3, `meshlab`, style
      - 4, `bw`, black and white style.

    :param int axes: axes type number

      - 0,  no axes,
      - 1,  draw three customizable gray grid walls. See ``show()`` documentation.
      - 2,  show cartesian axes from (0,0,0)
      - 3,  show positive range of cartesian axes from (0,0,0)
      - 4,  show a triad at bottom left
      - 5,  show a cube at bottom left
      - 6,  mark the corners of the bounding box
      - 7,  draw a simple ruler at the bottom of the window
      - 8,  show the `vtkCubeAxesActor` object,
      - 9,  show the bounding box outLine,
      - 10, show three circles representing the maximum bounding box.

    :param bool infinity: if True fugue point is set at infinity (no perspective effects)
    :param bool sharecam: if False each renderer will have an independent vtkCamera
    :param bool interactive: if True will stop after show() to allow interaction w/ window
    :param bool depthpeeling: depth-peel volumes along with the translucent geometry
    :param bool offscreen: if True will not show the rendering window

    :param float zoom: camera zooming factor
    :param viewup: camera view-up direction ['x','y','z', or a vector direction]
    :param float azimuth: add azimuth rotation of the scene, in degrees
    :param float elevation: add elevation rotation of the scene, in degrees
    :param float roll: add roll-type rotation of the scene, in degrees

    :param dict camera: Camera parameters can further be specified with a dictionary
        assigned to the ``camera`` keyword:
        (E.g. `show(camera={'pos':(1,2,3), 'thickness':1000,})`)

        - pos, `(list)`,  the position of the camera in world coordinates
        - focalPoint `(list)`, the focal point of the camera in world coordinates
        - viewup `(list)`, the view up direction for the camera
        - distance `(float)`, set the focal point to the specified distance from the camera position.
        - clippingRange `(float)`, distance of the near and far clipping planes along
            the direction of projection.

        - parallelScale `(float)`,
            scaling used for a parallel projection, i.e. the height of the viewport
            in world-coordinate distances. The default is 1. Note that the "scale" parameter works as
            an "inverse scale", larger numbers produce smaller images.
            This method has no effect in perspective projection mode.

        - thickness `(float)`,
            set the distance between clipping planes. This method adjusts the far clipping
            plane to be set a distance 'thickness' beyond the near clipping plane.

        - viewAngle `(float)`,
            the camera view angle, which is the angular height of the camera view
            measured in degrees. The default angle is 30 degrees.
            This method has no effect in parallel projection mode.
            The formula for setting the angle up for perfect perspective viewing is:
            angle = 2*atan((h/2)/d) where h is the height of the RenderWindow
            (measured by holding a ruler up to your screen) and d is the distance
            from your eyes to the screen.

    :param int interactorStyle: change the style of muose interaction of the scene
    :param bool q: exit python session after returning.
    """

    if len(inputobj) == 0:
        return interactive()

    mesh, u = _inputsort(inputobj)

    mode = options.pop("mode", 'mesh')
    ttime = options.pop("z", None)

    add = options.pop("add", False)

    wire = options.pop("wire", False)
    wireframe = options.pop("wireframe", None)
    if wireframe is not None:
        wire = wireframe

    c = options.pop("c", None)
    color = options.pop("color", None)
    if color is not None:
        c = color

    lc = options.pop("lc", None)

    alpha = options.pop("alpha", 1)
    lw = options.pop("lw", 0.5)
    ps = options.pop("ps", None)
    legend = options.pop("legend", None)
    scbar = options.pop("scalarbar", 'v')
    vmin = options.pop("vmin", None)
    vmax = options.pop("vmax", None)
    cmap = options.pop("cmap", None)
    bands = options.pop("bands", None)
    scale = options.pop("scale", 1)
    scaleMeshFactors = options.pop("scaleMeshFactors", [1,1,1])
    shading = options.pop("shading", None)
    text = options.pop("text", None)
    style = options.pop("style", 'vtk')
    isolns = options.pop("isolines", dict())
    warpZfactor = options.pop("warpZfactor", None)
    warpYfactor = options.pop("warpYfactor", None)
    lighting = options.pop("lighting", None)
    exterior = options.pop("exterior", False)
    fast = options.pop("fast", False)

    # refresh axes titles for axes type = 8 (vtkCubeAxesActor)
    settings.xtitle = options.pop("xtitle", 'x')
    settings.ytitle = options.pop("ytitle", 'y')
    settings.ztitle = options.pop("ztitle", 'z')
    if settings.plotter_instance:
        if settings.ytitle!='x':
            if 'at' in options.keys():
                at = options['at']
            else:
                at = 0
            aet = settings.plotter_instance.axes_instances
            if len(aet)>at and isinstance(aet[at], vtk.vtkCubeAxesActor):
                aet[at].SetXTitle(settings.xtitle)
        if settings.ytitle!='y':
            if 'at' in options.keys():
                at = options['at']
            else:
                at = 0
            aet = settings.plotter_instance.axes_instances
            if len(aet)>at and isinstance(aet[at], vtk.vtkCubeAxesActor):
                aet[at].SetYTitle(settings.ytitle)
        if settings.ytitle!='z':
            if 'at' in options.keys():
                at = options['at']
            else:
                at = 0
            aet = settings.plotter_instance.axes_instances
            if len(aet)>at and isinstance(aet[at], vtk.vtkCubeAxesActor):
                aet[at].SetZTitle(settings.ztitle)


    # change some default to emulate standard behaviours
    options['verbose'] = False # dont disturb
    if  style == 0 or style == 'vtk':
        font = 'courier'
        axes = options.pop('axes', None)
        if axes is None:
            options['axes'] = {
                    'xyGrid':False,
                    'yzGrid':False,
                    'zxGrid':False,
                   }
        else:
            options['axes'] = axes # put back
        if cmap is None:
            cmap = 'rainbow'
    elif style == 1 or style == 'matplotlib':
        font = 'courier'
        bg = options.pop('bg', None)
        if bg is None:
            options['bg'] = 'white'
        else:
            options['bg'] = bg
        axes = options.pop('axes', None)
        if axes is None:
            options['axes'] =  {
                    'xyGrid':False,
                    'yzGrid':False,
                    'zxGrid':False,
                   }
        else:
            options['axes'] = axes # put back
        if cmap is None:
            cmap = 'viridis'
    elif style == 2 or style == 'paraview':
        font = 'arial'
        bg = options.pop('bg', None)
        if bg is None:
            options['bg'] = (82, 87, 110)
        else:
            options['bg'] = bg
        if cmap is None:
            cmap = 'coolwarm'
    elif style == 3 or style == 'meshlab':
        font = 'courier'
        bg = options.pop('bg', None)
        if bg is None:
            options['bg'] = (8, 8, 16)
            options['bg2'] = (117, 117, 234)
        else:
            options['bg'] = bg
        axes = options.pop('axes', None)
        if axes is None:
            options['axes'] = 10
        else:
            options['axes'] = axes # put back
        if cmap is None:
            cmap = 'afmhot'
    elif style == 4 or style == 'bw':
        font = 'courier'
        bg = options.pop('bg', None)
        if bg is None:
            options['bg'] = (217, 255, 238)
        else:
            options['bg'] = bg
        axes = options.pop('axes', None)
        if axes is None:
            options['axes'] =  {
                    'xyGrid':False,
                    'yzGrid':False,
                    'zxGrid':False,
                   }
        else:
            options['axes'] = axes # put back
        if cmap is None:
            cmap = 'binary'


    #################################################################
    actors = []
    if add and settings.plotter_instance:
        actors = settings.plotter_instance.actors

    if mesh and ('mesh' in mode or 'color' in mode or 'warp' in mode or 'displac' in mode):
        if 'warp' in mode: #deprecation
            printc("~bomb Please use 'displacement' instead of 'warp' in mode!", c=1)

        actor = MeshActor(u, mesh, exterior=exterior, fast=fast)
        actor.wireframe(wire)
        actor.scale(scaleMeshFactors)
        if lighting:
            actor.lighting(lighting)
        if ttime:
            actor.z(ttime)
        if legend:
            actor.legend(legend)
        if c:
            actor.color(c)
        if lc:
            actor.lineColor(lc)
        if alpha:
            alpha = min(alpha, 1)
            actor.alpha(alpha*alpha)
        if lw:
            actor.lineWidth(lw)
            if wire and alpha:
                lw1 = min(lw, 1)
                actor.alpha(alpha*lw1)
        if ps:
            actor.pointSize(ps)
        if shading:
            if shading == 'phong':
                actor.phong()
            elif shading == 'flat':
                actor.flat()
            elif shading[0] == 'g':
                actor.gouraud()
        delta = None
        if cmap and u and c is None:
            delta = [u(p) for p in mesh.coordinates()]
            #delta = u.compute_vertex_values(mesh) # needs reshape
            if u.value_rank() > 0: # wiil show the size of the vector
                actor.pointColors(utils.mag(delta),
                                  cmap=cmap, bands=bands, vmin=vmin, vmax=vmax)
            else:
                actor.pointColors(delta, cmap=cmap, bands=bands, vmin=vmin, vmax=vmax)

        if scbar and c is None:
            if 'h' in scbar:
                actor.addScalarBar(horizontal=True,  vmin=vmin, vmax=vmax)
            else:
                actor.addScalarBar(horizontal=False, vmin=vmin, vmax=vmax)

        if 'warp' in mode or 'displac' in mode:
            if delta is None:
                delta = [u(p) for p in mesh.coordinates()]
            movedpts = mesh.coordinates() + delta
            actor.polydata(False).GetPoints().SetData(numpy_to_vtk(movedpts))
            actor.poly.GetPoints().Modified()
            actor.u_values = delta

        if warpZfactor:
            scals = actor.scalars(0)
            if len(scals):
                pts_act = actor.getPoints(copy=False)
                pts_act[:, 2] = scals*warpZfactor*scaleMeshFactors[2]
        if warpYfactor:
            scals = actor.scalars(0)
            if len(scals):
                pts_act = actor.getPoints(copy=False)
                pts_act[:, 1] = scals*warpYfactor*scaleMeshFactors[1]

        if len(isolns) > 0:
            ison = isolns.pop("n", 10)
            isocol = isolns.pop("c", 'black')
            isoalpha = isolns.pop("alpha", 1)
            isolw = isolns.pop("lw", 1)

            isos = actor.isolines(n=ison).color(isocol).lw(isolw).alpha(isoalpha)

            isoz = isolns.pop("z", None)
            if isoz is not None: # kind of hack to make isolines visible on flat meshes
                d = isoz
            else:
                d = actor.diagonalSize()/400
            isos.z(actor.z()+d)
            actors.append(isos)

        actors.append(actor)


    #################################################################
    if 'arrow' in mode or 'line' in mode:
        if 'arrow' in mode:
            arrs = MeshArrows(u, scale=scale)
        else:
            arrs = MeshLines(u, scale=scale)
        if legend and not 'mesh' in mode:
            arrs.legend(legend)
        if c:
            arrs.color(c)
            arrs.color(c)
        if alpha:
            arrs.alpha(alpha)
        actors.append(arrs)


    #################################################################
    if 'tensor' in mode:
        pass #todo


    #################################################################
    for ob in inputobj:
        inputtype = str(type(ob))
        if 'vtk' in inputtype:
           actors.append(ob)

    if text:
        textact = Text(text, font=font)
        actors.append(textact)

    if 'at' in options.keys() and 'interactive' not in options.keys():
        if settings.plotter_instance:
            N = settings.plotter_instance.shape[0]*settings.plotter_instance.shape[1]
            if options['at'] == N-1:
                options['interactive'] = True

    if settings.plotter_instance:
        for a2 in settings.collectable_actors:
            if isinstance(a2, vtk.vtkCornerAnnotation):
                if 0 in a2.renderedAt: # remove old message
                    settings.plotter_instance.remove(a2)
                    break

    return show(actors, **options)


###################################################################################
class MeshActor(Actor):
    """MeshActor, a vtkActor derived object for dolfin support."""

    def __init__(self, *inputobj, **options):

        c = options.pop("c", "gold")
        alpha = options.pop("alpha", 1)
        exterior = options.pop("exterior", False)
        fast = options.pop("fast", False)
        computeNormals = options.pop("computeNormals", False)

        mesh, u = _inputsort(inputobj)
        if not mesh:
            return

        if exterior:
            import dolfin
            meshc = dolfin.BoundaryMesh(mesh, 'exterior')
        else:
            meshc = mesh

        poly = utils.buildPolyData(meshc.coordinates(), meshc.cells(), fast=fast)

        Actor.__init__(self,
            poly,
            c=c,
            alpha=alpha,
            computeNormals=computeNormals,
        )

        self.mesh = mesh  # holds a dolfin Mesh obj
        self.u = u  # holds a dolfin function_data
        self.u_values = None  # holds the actual values of u on the mesh
        u_values = None

        if u:
            u_values = np.array([u(p) for p in self.mesh.coordinates()])
            #print(u_values)

        if u_values is not None:  # colorize if a dolfin function is passed
            if len(u_values.shape) == 2:
                if u_values.shape[1] in [2, 3]:  # u_values is 2D or 3D
                    self.u_values = u_values
                    dispsizes = utils.mag(u_values)
            else:  # u_values is 1D
                dispsizes = u_values

            self.addPointScalars(dispsizes, "u_values")#.mapPointsToCells()

    def move(self, u=None):
        if u is None:
            u = self.u
        delta = [u(p) for p in self.mesh.coordinates()]
        movedpts = self.mesh.coordinates() + delta
        self.polydata(False).GetPoints().SetData(numpy_to_vtk(movedpts))
        self.poly.GetPoints().Modified()
        self.u_values = delta

def MeshPoints(*inputobj, **options):
    """
    Build a point ``Actor`` for a list of points.

    :param float r: point radius.
    :param c: color name, number, or list of [R,G,B] colors of same length as plist.
    :type c: int, str, list
    :param float alpha: transparency in range [0,1].
    """
    r = options.pop("r", 5)
    c = options.pop("c", "gray")
    alpha = options.pop("alpha", 1)

    mesh, u = _inputsort(inputobj)
    if not mesh:
        return None
    plist = mesh.coordinates()
    if u:
        u_values = np.array([u(p) for p in plist])
    if len(plist[0]) == 2:  # coords are 2d.. not good..
        plist = np.insert(plist, 2, 0, axis=1)  # make it 3d
    if len(plist[0]) == 1:  # coords are 1d.. not good..
        plist = np.insert(plist, 1, 0, axis=1)  # make it 3d
        plist = np.insert(plist, 2, 0, axis=1)

    actor = shapes.Points(plist, r=r, c=c, alpha=alpha)

    actor.mesh = mesh
    if u:
        actor.u = u
        if len(u_values.shape) == 2:
            if u_values.shape[1] in [2, 3]:  # u_values is 2D or 3D
                actor.u_values = u_values
                dispsizes = utils.mag(u_values)
        else:  # u_values is 1D
            dispsizes = u_values
        actor.addPointScalars(dispsizes, "u_values")
    return actor


def MeshLines(*inputobj, **options):
    """
    Build the line segments between two lists of points `startPoints` and `endPoints`.
    `startPoints` can be also passed in the form ``[[point1, point2], ...]``.

    A dolfin ``Mesh`` that was deformed/modified by a function can be
    passed together as inputs.

    :param float scale: apply a rescaling factor to the length
    """
    scale = options.pop("scale", 1)
    lw = options.pop("lw", 1)
    c = options.pop("c", None)
    alpha = options.pop("alpha", 1)

    mesh, u = _inputsort(inputobj)
    if not mesh:
        return None

    startPoints = mesh.coordinates()
    u_values = np.array([u(p) for p in mesh.coordinates()])
    if not utils.isSequence(u_values[0]):
        printc("~times Error: cannot show Lines for 1D scalar values!", c=1)
        raise RuntimeError()
    endPoints = mesh.coordinates() + u_values
    if u_values.shape[1] == 2:  # u_values is 2D
        u_values = np.insert(u_values, 2, 0, axis=1)  # make it 3d
        startPoints = np.insert(startPoints, 2, 0, axis=1)  # make it 3d
        endPoints = np.insert(endPoints, 2, 0, axis=1)  # make it 3d

    actor = shapes.Lines(
        startPoints, endPoints, scale=scale, lw=lw, c=c, alpha=alpha
    )

    actor.mesh = mesh
    actor.u = u
    actor.u_values = u_values
    return actor


def MeshArrows(*inputobj, **options):
    """
    Build arrows representing displacements.

    :param float s: cross-section size of the arrow
    :param float rescale: apply a rescaling factor to the length
    """
    s = options.pop("s", None)
    scale = options.pop("scale", 1)
    c = options.pop("c", "gray")
    alpha = options.pop("alpha", 1)
    res = options.pop("res", 12)

    mesh, u = _inputsort(inputobj)
    if not mesh:
        return None

    startPoints = mesh.coordinates()
    u_values = np.array([u(p) for p in mesh.coordinates()])
    if not utils.isSequence(u_values[0]):
        printc("~times Error: cannot show Arrows for 1D scalar values!", c=1)
        raise RuntimeError()
    endPoints = mesh.coordinates() + u_values
    if u_values.shape[1] == 2:  # u_values is 2D
        u_values = np.insert(u_values, 2, 0, axis=1)  # make it 3d
        startPoints = np.insert(startPoints, 2, 0, axis=1)  # make it 3d
        endPoints = np.insert(endPoints, 2, 0, axis=1)  # make it 3d

    actor = shapes.Arrows(
        startPoints, endPoints, s=s, scale=scale, c=c, alpha=alpha, res=res
    )
    actor.mesh = mesh
    actor.u = u
    actor.u_values = u_values
    return actor

