from __future__ import division, print_function
import time
import sys
import vtk
import numpy
import os

from vtkplotter import __version__
import vtkplotter.vtkio as vtkio
import vtkplotter.utils as utils
import vtkplotter.colors as colors
from vtkplotter.actors import Actor, Assembly, Volume
import vtkplotter.docs as docs
import vtkplotter.settings as settings
import vtkplotter.addons as addons
from vtk.util.numpy_support import vtk_to_numpy

__doc__ = (
    """
Defines main class ``Plotter`` to manage actors and 3D rendering.
"""
    + docs._defs
)

__all__ = ["show", "clear", "Plotter",
           "closeWindow", "closePlotter", "interactive"]

########################################################################
def show(*actors, **options):
    """
    Create on the fly an instance of class ``Plotter`` and show the object(s) provided.

    Allowed input objects are: ``filename``, ``vtkPolyData``, ``vtkActor``,
    ``vtkActor2D``, ``vtkImageActor``, ``vtkAssembly`` or ``vtkVolume``.

    If filename is given, its type is guessed based on its extension.
    Supported formats are:
    `vtu, vts, vtp, ply, obj, stl, 3ds, xml, neutral, gmsh, pcd, xyz, txt, byu,
    tif, slc, vti, mhd, png, jpg`.

    :param int at: number of the renderer to plot to, if more than one exists
    :param int axes: set the type of axes to be shown

          - 0,  no axes,
          - 1,  draw three gray grid walls
          - 2,  show cartesian axes from (0,0,0)
          - 3,  show positive range of cartesian axes from (0,0,0)
          - 4,  show a triad at bottom left
          - 5,  show a cube at bottom left
          - 6,  mark the corners of the bounding box
          - 7,  draw a simple ruler at the bottom of the window
          - 8,  show the ``vtkCubeAxesActor`` object,
          - 9,  show the bounding box outLine,
          - 10, show three circles representing the maximum bounding box

    :param c:     surface color, in rgb, hex or name formats
    :param bc:    set a color for the internal surface face
    :param bool wire:  show actor in wireframe representation
    :param float azimuth/elevation/roll:  move camera accordingly
    :param str viewup:  either ['x', 'y', 'z'] or a vector to set vertical direction
    :param bool resetcam:  re-adjust camera position to fit objects

    :param dict camera: Camera parameters can further be specified with a dictionary
        assigned to the ``camera`` keyword (E.g. `show(camera={'pos':(1,2,3), 'thickness':1000,})`):

        - pos, `(list)`,  the position of the camera in world coordinates
        - focalPoint `(list)`, the focal point of the camera in world coordinates
        - viewup `(list)`, the view up direction for the camera
        - distance `(float)`, set the focal point to the specified distance from the camera position.
        - clippingRange `(float)`, distance of the near and far clipping planes along the direction
            of projection.

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

    :param bool interactive:  pause and interact with window (True)
        or continue execution (False)
    :param float rate:  maximum rate of `show()` in Hertz
    :param int interactorStyle: set the type of interaction

        - 0, TrackballCamera
        - 1, TrackballActor
        - 2, JoystickCamera
        - 3, Unicam
        - 4, Flight
        - 5, RubberBand3D
        - 6, RubberBandZoom

    :param bool q:  force program to quit after `show()` command returns.

    :param bool newPlotter: if set to `True`, a call to ``show`` will instantiate
        a new ``Plotter`` object (a new window) instead of reusing the first created.
        See e.g.: |readVolumeAsIsoSurface.py|_
    :return: the current ``Plotter`` class instance.

    .. note:: With multiple renderers, keyword ``at`` can become a `list`, e.g.

        .. code-block:: python

            from vtkplotter import *
            s = Sphere()
            c = Cube()
            p = Paraboloid()
            show(s, c, at=[0, 1], shape=(3,1))
            show(p, at=2, interactive=True)
            #
            # is equivalent to:
            vp = Plotter(shape=(3,1))
            s = Sphere()
            c = Cube()
            p = Paraboloid()
            vp.show(s, at=0)
            vp.show(p, at=1)
            vp.show(c, at=2, interactive=True)
    """
    at = options.pop("at", None)
    shape = options.pop("shape", (1, 1))
    N = options.pop("N", None)
    pos = options.pop("pos", (0, 0))
    size = options.pop("size", "auto")
    screensize = options.pop("screensize", "auto")
    title = options.pop("title", "")
    bg = options.pop("bg", "blackboard")
    bg2 = options.pop("bg2", None)
    axes = options.pop("axes", 4)
    infinity = options.pop("infinity", False)
    verbose = options.pop("verbose", True)
    interactive = options.pop("interactive", None)
    offscreen = options.pop("offscreen", False)
    sharecam = options.pop("sharecam", True)
    resetcam = options.pop("resetcam", True)
    zoom = options.pop("zoom", None)
    viewup = options.pop("viewup", "")
    azimuth = options.pop("azimuth", 0)
    elevation = options.pop("elevation", 0)
    roll = options.pop("roll", 0)
    camera = options.pop("camera", None)
    interactorStyle = options.pop("interactorStyle", 0)
    newPlotter = options.pop("newPlotter", False)
    depthpeeling = options.pop("depthpeeling", False)
    q = options.pop("q", False)

    if len(actors) == 0:
        actors = None
    elif len(actors) == 1:
        actors = actors[0]
    else:
        actors = utils.flatten(actors)

    if settings.plotter_instance and newPlotter == False:
        vp = settings.plotter_instance
    else:
        if utils.isSequence(at):
            if not utils.isSequence(actors):
                colors.printc("~times show() Error: input must be a list.", c=1)
                raise RuntimeError()
            if len(at) != len(actors):
                colors.printc("~times show() Error: lists 'input' and 'at', must have equal lengths.", c=1)
                raise RuntimeError()
            if len(at) > 1 and (shape == (1, 1) and N == None):
                N = max(at) + 1
        elif at is None and (N or shape != (1, 1)):
            if not utils.isSequence(actors):
                colors.printc('~times show() Error: N or shape is set, but input is not a sequence.', c=1)
                colors.printc('              you may need to specify e.g. at=0', c=1)
                raise RuntimeError()
            at = range(len(actors))

        vp = Plotter(
            shape=shape,
            N=N,
            pos=pos,
            size=size,
            screensize=screensize,
            title=title,
            bg=bg,
            bg2=bg2,
            axes=axes,
            sharecam=sharecam,
            infinity=infinity,
            depthpeeling=depthpeeling,
            verbose=verbose,
            interactive=interactive,
            offscreen=offscreen,
        )

    # use _vp_to_return because vp.show() can return a k3d/panel plot
    if utils.isSequence(at):
        for i, a in enumerate(actors):
            _vp_to_return = vp.show(
                a,
                at=i,
                zoom=zoom,
                resetcam=resetcam,
                viewup=viewup,
                azimuth=azimuth,
                elevation=elevation,
                roll=roll,
                camera=camera,
                interactive=interactive,
                interactorStyle=interactorStyle,
                q=q,
            )
        vp.interactor.Start()
    else:
        _vp_to_return = vp.show(
            actors,
            at=at,
            zoom=zoom,
            resetcam=resetcam,
            viewup=viewup,
            azimuth=azimuth,
            elevation=elevation,
            roll=roll,
            camera=camera,
            interactive=interactive,
            interactorStyle=interactorStyle,
            q=q,
        )

    return _vp_to_return


def interactive():
    """Go back to the rendering window interaction mode."""
    if settings.plotter_instance:
        if hasattr(settings.plotter_instance, 'interactor'):
            if settings.plotter_instance.interactor:
                settings.plotter_instance.interactor.Start()
    return settings.plotter_instance


def clear(actor=()):
    """
    Clear specific actor or list of actors from the current rendering window.
    """
    if not settings.plotter_instance:
        return
    settings.plotter_instance.clear(actor)
    return settings.plotter_instance


def closeWindow(plotterInstance=None):
    """Close the current or the input rendering window."""
    if not plotterInstance:
        from vtkplotter.settings import plotter_instance
        plotterInstance  = plotter_instance
        if not plotterInstance:
            return
    plotterInstance.interactor.ExitCallback()
    plotterInstance.closeWindow()
    return plotterInstance


def closePlotter():
    """Close the current instance of ``Plotter`` and its rendering window."""
#    if settings.notebook_plotter:
#        settings.notebook_plotter.close()
    if settings.plotter_instance:
        settings.plotter_instance.closeWindow()
        settings.plotter_instance = None
        settings.plotter_instances = []
        settings.collectable_actors = []
    return None


########################################################################
class Plotter:
    """
    Main class to manage actors.

    :param list shape: shape of the grid of renderers in format (rows, columns).
        Ignored if N is specified.
    :param int N: number of desired renderers arranged in a grid automatically.
    :param list pos: (x,y) position in pixels of top-left corner of the rendering window
        on the screen
    :param size: size of the rendering window. If 'auto', guess it based on screensize.
    :param screensize: physical size of the monitor screen
    :param bg: background color or specify jpg image file name with path
    :param bg2: background color of a gradient towards the top
    :param int axes:

      - 0,  no axes
      - 1,  draw three gray grid walls
      - 2,  show cartesian axes from (0,0,0)
      - 3,  show positive range of cartesian axes from (0,0,0)
      - 4,  show a triad at bottom left
      - 5,  show a cube at bottom left
      - 6,  mark the corners of the bounding box
      - 7,  draw a simple ruler at the bottom of the window
      - 8,  show the ``vtkCubeAxesActor`` object
      - 9,  show the bounding box outLine,
      - 10, show three circles representing the maximum bounding box.

    Axis type-1 can be fully customized by passing a dictionary ``axes=dict()`` where:

        - `xtitle`,            ['x'], x-axis title text.
        - `ytitle`,            ['y'], y-axis title text.
        - `ztitle`,            ['z'], z-axis title text.
        - `numberOfDivisions`, [automatic], number of divisions on the shortest axis
        - `axesLineWidth`,       [1], width of the axes lines
        - `gridLineWidth`,       [1], width of the grid lines
        - `reorientShortTitle`, [True], titles shorter than 2 letter are placed horizontally
        - `originMarkerSize`, [0.01], draw a small cube on the axis where the origin is
        - `enableLastLabel`, [False], show last numeric label on axes
        - `titleDepth`,          [0], extrusion fractional depth of title text
        - `xyGrid`,           [True], show a gridded wall on plane xy
        - `yzGrid`,           [True], show a gridded wall on plane yz
        - `zxGrid`,           [True], show a gridded wall on plane zx
        - `zxGrid2`,         [False], show zx plane on opposite side of the bounding box
        - `xyGridTransparent`  [False], make grid plane completely transparent
        - `xyGrid2Transparent` [False], make grid plane completely transparent on opposite side box
        - `xyPlaneColor`,   ['gray'], color of the plane
        - `xyGridColor`,    ['gray'], grid line color
        - `xyAlpha`,          [0.15], grid plane opacity
        - `showTicks`,        [True], show major ticks
        - `xTitlePosition`,   [0.32], title fractional positions along axis
        - `xTitleOffset`,     [0.05], title fractional offset distance from axis line
        - `xTitleJustify`, ["top-right"], title justification
        - `xTitleRotation`,      [0], add a rotation of the axis title
        - `xLineColor`,  [automatic], color of the x-axis
        - `xTitleColor`, [automatic], color of the axis title
        - `xTitleBackfaceColor`, [None],  color of axis title on its backface
        - `xTitleSize`,      [0.025], size of the axis title
        - `xHighlightZero`,   [True], draw a line highlighting zero position if in range
        - `xHighlightZeroColor`, [automatic], color of the line highlighting the zero position
        - `xTickRadius`,     [0.005], radius of the major ticks
        - `xTickThickness`, [0.0025], thickness of the major ticks along their axis
        - `xTickColor`,  [automatic], color of major ticks
        - `xMinorTicks`,         [1], number of minor ticks between two major ticks
        - `tipSize`,          [0.01], size of the arrow tip
        - `xLabelPrecision`,     [2], nr. of significative digits to be shown
        - `xLabelSize`,      [0.015], size of the numeric labels along axis
        - `xLabelOffset`,    [0.025], offset of numeric labels

    :param bool infinity: if True fugue point is set at infinity (no perspective effects)
    :param bool sharecam: if False each renderer will have an independent vtkCamera
    :param bool interactive: if True will stop after show() to allow interaction w/ window
    :param bool offscreen: if True will not show the rendering window
    :param bool depthpeeling: depth-peel volumes along with the translucent geometry
    :param QVTKRenderWindowInteractor qtWidget:

      render in a Qt-Widget using an QVTKRenderWindowInteractor.
      Overrides offscreen to True
      Overides interactive to False
      Sets setting.usingQt to True
      See Also: example qt_windows.py

    |multiwindows|
    """

    def __init__(
        self,
        shape=(1, 1),
        N=None,
        pos=(0, 0),
        size="auto",
        screensize="auto",
        title="",
        bg="blackboard",
        bg2=None,
        axes=4,
        infinity=False,
        sharecam=True,
        verbose=True,
        interactive=None,
        offscreen=False,
        depthpeeling=False,
        qtWidget = None
    ):

        settings.plotter_instance = self
        settings.plotter_instances.append(self)

        if qtWidget is not None:
              # overrides the interactive and offscreen properties
            interactive = False
            offscreen = True
            settings.usingQt = True

        if interactive is None:
            if N or shape != (1, 1):
                interactive = False
            else:
                interactive = True

        if not interactive:
            verbose = False

        self.verbose = verbose
        self.actors = []  # list of actors to be shown
        self.clickedActor = None  # holds the actor that has been clicked
        self.renderer = None  # current renderer
        self.renderers = []  # list of renderers
        self.shape = shape
        self.pos = pos
        self.interactive = interactive  # allows to interact with renderer
        self.axes = axes  # show axes type nr.
        self.title = title  # window title
        self.sharecam = sharecam  # share the same camera if multiple renderers
        self.infinity = infinity  # ParallelProjection On or Off
        self._legend = []  # list of legend entries for actors
        self.legendSize = 0.15  # size of legend
        self.legendBC = (0.96, 0.96, 0.9)  # legend background color
        self.legendPos = 2  # 1=topright, 2=top-right, 3=bottom-left
        self.picked3d = None  # 3d coords of a clicked point on an actor
        self.backgrcol = bg
        self.offscreen = offscreen
        self.showFrame = True
        self.qtWidget = qtWidget # (QVTKRenderWindowInteractor)

        # mostly internal stuff:
        self.justremoved = None
        self.axes_instances = []
        self.icol = 0
        self.clock = 0
        self._clockt0 = time.time()
        self.initializedPlotter = False
        self.initializedIren = False
        self.keyPressFunction = None
        self.sliders = []
        self.buttons = []
        self.widgets = []
        self.scalarbars = []
        self.cutterWidget = None
        self.backgroundRenderer = None
        self.mouseLeftClickFunction = None
        self.mouseMiddleClickFunction = None
        self.mouseRightClickFunction = None
        self._first_viewup = True

        self.xtitle = settings.xtitle  # x axis label and units
        self.ytitle = settings.ytitle  # y axis label and units
        self.ztitle = settings.ztitle  # z axis label and units


        if settings.notebookBackend:
            self.interactive = False
            self.interactor = None
            self.window = None
            if size == "auto":
                self.size = (1000, 1000)
            ############################
            return #####################
            ############################


        # build the renderering window:
        if settings.useOpenVR:
            self.camera = vtk.vtkOpenVRCamera()
            self.window =vtk.vtkOpenVRRenderWindow()
        else:
            self.camera = vtk.vtkCamera()
            self.window = vtk.vtkRenderWindow()

        self.window.PointSmoothingOn()

        # sort out screen size
        if screensize == "auto":
            aus = self.window.GetScreenSize()
            if aus and len(aus) == 2 and aus[0] > 100 and aus[1] > 100:  # seems ok
                if aus[0] / aus[1] > 2:  # looks like there are 2 or more screens
                    screensize = (int(aus[0] / 2), aus[1])
                else:
                    screensize = aus
            else:  # it went wrong, use a default 1.5 ratio
                screensize = (2160, 1440)

        x, y = screensize
        if N:  # N = number of renderers. Find out the best
            if shape != (1, 1):  # arrangement based on minimum nr. of empty renderers
                colors.printc("Warning: having set N, shape is ignored.", c=1)
            nx = int(numpy.sqrt(int(N * y / x) + 1))
            ny = int(numpy.sqrt(int(N * x / y) + 1))
            lm = [
                (nx, ny),
                (nx, ny + 1),
                (nx - 1, ny),
                (nx + 1, ny),
                (nx, ny - 1),
                (nx - 1, ny + 1),
                (nx + 1, ny - 1),
                (nx + 1, ny + 1),
                (nx - 1, ny - 1),
            ]
            ind, minl = 0, 1000
            for i, m in enumerate(lm):
                l = m[0] * m[1]
                if N <= l < minl:
                    ind = i
                    minl = l
            shape = lm[ind]

        if size == "auto":  # figure out a reasonable window size
            f = 1.5
            xs = y / f * shape[1]  # because y<x
            ys = y / f * shape[0]
            if xs > x / f:  # shrink
                xs = x / f
                ys = xs / shape[1] * shape[0]
            if ys > y / f:
                ys = y / f
                xs = ys / shape[0] * shape[1]
            self.size = (int(xs), int(ys))
            if shape == (1, 1):
                self.size = (int(y / f), int(y / f))  # because y<x
        else:
            self.size = (size[1], size[0])


        ############################
        self.shape = shape

        if sum(shape) > 3:
            self.legendSize *= 2

        for i in reversed(range(shape[0])):
            for j in range(shape[1]):
                if settings.useOpenVR:
                    arenderer = vtk.vtkOpenVRRenderer()
                else:
                    arenderer = vtk.vtkRenderer()
                arenderer.SetUseHiddenLineRemoval(settings.hiddenLineRemoval)
                arenderer.SetUseDepthPeeling(depthpeeling)
                if "jpg" in str(self.backgrcol).lower() or "jpeg" in str(self.backgrcol).lower():
                    if i == 0:
                        jpeg_reader = vtk.vtkJPEGReader()
                        if not jpeg_reader.CanReadFile(self.backgrcol):
                            colors.printc("~times Error reading background image file", self.backgrcol, c=1)
                            raise RuntimeError()
                        jpeg_reader.SetFileName(self.backgrcol)
                        jpeg_reader.Update()
                        image_data = jpeg_reader.GetOutput()
                        image_actor = vtk.vtkImageActor()
                        image_actor.InterpolateOn()
                        image_actor.SetInputData(image_data)
                        self.backgroundRenderer = vtk.vtkRenderer()
                        self.backgroundRenderer.SetLayer(0)
                        self.backgroundRenderer.InteractiveOff()
                        if bg2:
                            self.backgroundRenderer.SetBackground(colors.getColor(bg2))
                        else:
                            self.backgroundRenderer.SetBackground(1, 1, 1)
                        arenderer.SetLayer(1)
                        self.window.SetNumberOfLayers(2)
                        self.window.AddRenderer(self.backgroundRenderer)
                        self.backgroundRenderer.AddActor(image_actor)
                else:
                    arenderer.SetBackground(colors.getColor(self.backgrcol))
                    if bg2:
                        arenderer.GradientBackgroundOn()
                        arenderer.SetBackground2(colors.getColor(bg2))
                x0 = i / shape[0]
                y0 = j / shape[1]
                x1 = (i + 1) / shape[0]
                y1 = (j + 1) / shape[1]
                arenderer.SetViewport(y0, x0, y1, x1)
                self.renderers.append(arenderer)
                self.axes_instances.append(None)

        if "full" in size and not offscreen:  # full screen
            self.window.SetFullScreen(True)
            self.window.BordersOn()
        else:
            self.window.SetSize(int(self.size[0]), int(self.size[1]))

        self.window.SetPosition(pos)

        if not title:
            title = " vtkplotter " + __version__ + ", vtk " + vtk.vtkVersion().GetVTKVersion()
            title += ", python " + str(sys.version_info[0]) + "." + str(sys.version_info[1])

        self.window.SetWindowName(title)

        if not settings.usingQt:
            for r in self.renderers:
                self.window.AddRenderer(r)

        if self.qtWidget is not None:
            self.interactor = self.qtWidget.GetRenderWindow().GetInteractor()
            self.window.SetOffScreenRendering(True)
            return

        if offscreen:
            self.window.SetOffScreenRendering(True)
            self.interactive = False
            self.interactor = None
            ########################
            return
            ########################

        if settings.useOpenVR:
            self.interactor = vtk.vtkOpenVRRenderWindowInteractor()
        else:
            self.interactor = vtk.vtkRenderWindowInteractor()
        self.interactor.SetRenderWindow(self.window)
        vsty = vtk.vtkInteractorStyleTrackballCamera()
        self.interactor.SetInteractorStyle(vsty)

        self.interactor.AddObserver("LeftButtonPressEvent", self._mouseleft)
        self.interactor.AddObserver("RightButtonPressEvent", self._mouseright)
        self.interactor.AddObserver("MiddleButtonPressEvent", self._mousemiddle)
        self.interactor.AddObserver("KeyPressEvent", self._keypress)

        if settings.allowInteraction:
            self._update_observer = None
            self._update_win_clock = time.time()

            def win_interact(iren, event):  # flushing renderer events
                if event == "TimerEvent":
                    iren.TerminateApp()

            self.interactor.AddObserver("TimerEvent", win_interact)

            def _allowInteraction():
                timenow = time.time()
                if timenow - self._update_win_clock > 0.1:
                    self._update_win_clock = timenow
                    self._update_observer = self.interactor.CreateRepeatingTimer(1)
                    if hasattr(self, 'interactor') and self.interactor:
                        self.interactor.Start()

                    if hasattr(self, 'interactor') and self.interactor:
                        # twice otherwise it crashes when pressing Esc (??)
                        self.interactor.DestroyTimer(self._update_observer)

            self.allowInteraction = _allowInteraction


    def __str__(self):
        utils.printInfo(self)
        return ""

    def __iadd__(self, actors):
        self.add(actors, render=False)
        return self

    def __isub__(self, actors):
        self.remove(actors)
        return self

    def add(self, actors, render=True):
        """Append input object to the internal list of actors to be shown.

        :return: returns input actor for possible concatenation.
        """
        if utils.isSequence(actors):
            for a in actors:
                if a not in self.actors:
                    self.actors.append(a)
                    if render and self.renderer:
                        self.renderer.AddActor(a)
            if render and self.interactor:
                self.interactor.Render()
            return None
        else:
            self.actors.append(actors)
            if render and self.renderer:
                self.renderer.AddActor(actors)
                if self.interactor:
                    self.interactor.Render()
            return actors

    def remove(self, actors):
        """Remove ``vtkActor`` or actor index from current renderer."""
        if not utils.isSequence(actors):
            actors = [actors]
        for a in actors:
            if self.renderer:
                self.renderer.RemoveActor(a)
                if hasattr(a, 'renderedAt'):
                    ir = self.renderers.index(self.renderer)
                    a.renderedAt.discard(ir)
            if a in self.actors:
                i = self.actors.index(a)
                del self.actors[i]

    ####################################################
    def load(self, inputobj, c=None, alpha=1, threshold=False, spacing=(), unpack=True):
        """
        Load Actors and Volumes from file.
        The output will depend on the file extension. See examples below.

        :param c: color in RGB format, hex, symbol or name
        :param alpha: transparency (0=invisible)

        For volumetric data (tiff, slc, vti etc):
        :param float threshold: value to draw the isosurface, False by default to return a ``Volume``
        :param list spacing: specify the voxel spacing in the three dimensions
        :param bool unpack: only for multiblock data, if True returns a flat list of objects.

        :Example:
            .. code-block:: python

                from vtkplotter import datadir, load, show

                # Return an Actor
                g = load(datadir+'ring.gmsh')
                show(g)

                # Return a list of 2 Actors
                g = load([datadir+'250.vtk', datadir+'290.vtk'])
                show(g)

                # Return a list of actors by reaading all files in a directory
                # (if directory contains DICOM files then a Volume is returned)
                g = load(datadir+'timecourse1d/')
                show(g)

                # Return a Volume. Color/Opacity transfer function can be specified too.
                g = load(datadir+'embryo.slc')
                g.c(['y','lb','w']).alpha((0.0, 0.4, 0.9, 1))
                show(g)

                # Return an Actor from a SLC volume with automatic thresholding
                g = load(datadir+'embryo.slc', threshold=True)
                show(g)
        """
        acts = vtkio.load(inputobj, c, alpha, threshold, spacing, unpack)
        if utils.isSequence(acts):
            self.actors += acts
        else:
            self.actors.append(acts)
        return acts


    def getVolumes(self, obj=None, renderer=None):
        """
        Return the list of the rendered Volumes.

        If ``obj`` is:
            ``None``, return volumes of current renderer

            ``int``, return volumes in given renderer number

        :param int,vtkRenderer renderer: specify which renederer to look into.
        """
        if renderer is None:
            renderer = self.renderer
        elif isinstance(renderer, int):
                renderer = self.renderers.index(renderer)
        else:
            return []

        if obj is None or isinstance(obj, int):
            if obj is None:
                acs = renderer.GetVolumes()
            elif obj >= len(self.renderers):
                colors.printc("~timesError in getVolumes: non existing renderer", obj, c=1)
                return []
            else:
                acs = self.renderers[obj].GetVolumes()
            vols = []
            acs.InitTraversal()
            for i in range(acs.GetNumberOfItems()):
                a = acs.GetNextItem()
                if a.GetPickable():
                    r = self.renderers.index(renderer)
                    if a == self.axes_instances[r]:
                        continue
                    vols.append(a)
            return vols


    def getActors(self, obj=None, renderer=None):
        """
        Return an actors list (which may include Volume objects too).

        If ``obj`` is:
            ``None``, return actors of current renderer

            ``int``, return actors in given renderer number

            ``vtkAssembly`` return the contained actors

            ``string``, return actors matching legend name

        :param int,vtkRenderer renderer: specify which renederer to look into.
        """
        if renderer is None:
            renderer = self.renderer
        elif isinstance(renderer, int):
                renderer = self.renderers.index(renderer)
        else:
            return []

        if obj is None or isinstance(obj, int):
            if obj is None:
                acs = renderer.GetActors()
            elif obj >= len(self.renderers):
                colors.printc("~timesError in getActors: non existing renderer", obj, c=1)
                return []
            else:
                acs = self.renderers[obj].GetActors()

            actors = []
            acs.InitTraversal()
            for i in range(acs.GetNumberOfItems()):
                a = acs.GetNextItem()
                if a.GetPickable():
                    r = self.renderers.index(renderer)
                    if a == self.axes_instances[r]:
                        continue
                    actors.append(a)
            return actors

        elif isinstance(obj, vtk.vtkAssembly):
            cl = vtk.vtkPropCollection()
            obj.GetActors(cl)
            actors = []
            cl.InitTraversal()
            for i in range(obj.GetNumberOfPaths()):
                act = vtk.vtkActor.SafeDownCast(cl.GetNextProp())
                if act.GetPickable():
                    actors.append(act)
            return actors

        elif isinstance(obj, str):  # search the actor by the legend name
            actors = []
            for a in self.actors:
                if hasattr(a, "_legend") and obj in a._legend:
                    actors.append(a)
            return actors

        elif isinstance(obj, vtk.vtkActor):
            return [obj]

        if self.verbose:
            colors.printc("~lightning Warning in getActors: unexpected input type", obj, c=1)
        return []


    def moveCamera(self, camstart, camstop, fraction):
        """
        Takes as input two ``vtkCamera`` objects and returns a
        new ``vtkCamera`` that is at an intermediate position:

        fraction=0 -> camstart,  fraction=1 -> camstop.

        Press ``shift-C`` key in interactive mode to dump a python snipplet
        of parameters for the current camera view.
        """
        if isinstance(fraction, int):
            colors.printc("~lightning Warning in moveCamera(): fraction should not be an integer", c=1)
        if fraction > 1:
            colors.printc("~lightning Warning in moveCamera(): fraction is > 1", c=1)
        cam = vtk.vtkCamera()
        cam.DeepCopy(camstart)
        p1 = numpy.array(camstart.GetPosition())
        f1 = numpy.array(camstart.GetFocalPoint())
        v1 = numpy.array(camstart.GetViewUp())
        c1 = numpy.array(camstart.GetClippingRange())
        s1 = camstart.GetDistance()

        p2 = numpy.array(camstop.GetPosition())
        f2 = numpy.array(camstop.GetFocalPoint())
        v2 = numpy.array(camstop.GetViewUp())
        c2 = numpy.array(camstop.GetClippingRange())
        s2 = camstop.GetDistance()
        cam.SetPosition(p2 * fraction + p1 * (1 - fraction))
        cam.SetFocalPoint(f2 * fraction + f1 * (1 - fraction))
        cam.SetViewUp(v2 * fraction + v1 * (1 - fraction))
        cam.SetDistance(s2 * fraction + s1 * (1 - fraction))
        cam.SetClippingRange(c2 * fraction + c1 * (1 - fraction))
        self.camera = cam
        save_int = self.interactive
        self.show(resetcam=0, interactive=0)
        self.interactive = save_int

    ################################################################## AddOns
    def addLight(
        self,
        pos=(1, 1, 1),
        focalPoint=(0, 0, 0),
        deg=90,
        ambient=None,
        diffuse=None,
        specular=None,
        showsource=False,
    ):
        """
        Generate a source of light placed at pos, directed to focal point fp.

        :param fp: focal Point, if this is a ``vtkActor`` use its position.
        :type fp: vtkActor, list
        :param deg: aperture angle of the light source
        :param showsource: if `True`, will show a vtk representation
                            of the source of light as an extra actor

        .. hint:: |lights.py|_
        """
        if isinstance(focalPoint, vtk.vtkActor):
            focalPoint = focalPoint.GetPosition()
        light = vtk.vtkLight()
        light.SetLightTypeToSceneLight()
        light.SetPosition(pos)
        light.SetPositional(1)
        light.SetConeAngle(deg)
        light.SetFocalPoint(focalPoint)
        if diffuse  is not None: light.SetDiffuseColor(colors.getColor(diffuse))
        if ambient  is not None: light.SetAmbientColor(colors.getColor(ambient))
        if specular is not None: light.SetSpecularColor(colors.getColor(specular))
        if showsource:
            lightActor = vtk.vtkLightActor()
            lightActor.SetLight(light)
            self.renderer.AddViewProp(lightActor)
        self.renderer.AddLight(light)
        return light

    def addScalarBar(self, actor=None, c=None, title="", horizontal=False, vmin=None, vmax=None):
        """Add a 2D scalar bar for the specified actor.

        If `actor` is ``None`` will add it to the last actor in ``self.actors``.

        |mesh_bands| |mesh_bands.py|_
        """
        return addons.addScalarBar(actor, c, title, horizontal, vmin, vmax)

    def addScalarBar3D(
        self,
        obj=None,
        at=0,
        pos=(0, 0, 0),
        normal=(0, 0, 1),
        sx=0.1,
        sy=2,
        nlabels=9,
        ncols=256,
        cmap=None,
        c=None,
        alpha=1,
    ):
        """Draw a 3D scalar bar.

        ``obj`` input can be:
            - a list of numbers,
            - a list of two numbers in the form `(min, max)`,
            - a ``vtkActor`` already containing a set of scalars associated to vertices or cells,
            - if ``None`` the last actor in the list of actors will be used.

        |scalbar| |mesh_coloring.py|_
        """
        return addons.addScalarBar3D(obj, at, pos, normal, sx, sy, nlabels, ncols, cmap, c, alpha)

    def addSlider2D(
        self, sliderfunc, xmin, xmax, value=None, pos=4, title="", c=None, showValue=True
    ):
        """Add a slider widget which can call an external custom function.

        :param sliderfunc: external function to be called by the widget
        :param float xmin:  lower value
        :param float xmax:  upper value
        :param float value: current value
        :param list pos:  position corner number: horizontal [1-4] or vertical [11-14]
                            it can also be specified by corners coordinates [(x1,y1), (x2,y2)]
        :param str title: title text
        :param bool showValue:  if true current value is shown

        |sliders| |sliders.py|_
        """
        return addons.addSlider2D(sliderfunc, xmin, xmax, value, pos, title, c, showValue)

    def addSlider3D(
        self,
        sliderfunc,
        pos1,
        pos2,
        xmin,
        xmax,
        value=None,
        s=0.03,
        title="",
        rotation=0,
        c=None,
        showValue=True,
    ):
        """Add a 3D slider widget which can call an external custom function.

        :param sliderfunc: external function to be called by the widget
        :param list pos1: first position coordinates
        :param list pos2: second position coordinates
        :param float xmin:  lower value
        :param float xmax:  upper value
        :param float value: initial value
        :param float s: label scaling factor
        :param str title: title text
        :param c: slider color
        :param float rotation: title rotation around slider axis
        :param bool showValue: if True current value is shown

        |sliders3d| |sliders3d.py|_
        """
        return addons.addSlider3D(
            sliderfunc, pos1, pos2, xmin, xmax, value, s, title, rotation, c, showValue
        )

    def addButton(
        self,
        fnc,
        states=("On", "Off"),
        c=("w", "w"),
        bc=("dg", "dr"),
        pos=(20, 40),
        size=24,
        font="arial",
        bold=False,
        italic=False,
        alpha=1,
        angle=0,
    ):
        """Add a button to the renderer window.

        :param list states: a list of possible states, e.g. ['On', 'Off']
        :param c:      a list of colors for each state
        :param bc:     a list of background colors for each state
        :param pos:    2D position in pixels from left-bottom corner
        :param size:   size of button font
        :param str font:   font type (arial, courier, times)
        :param bool bold:   bold face (False)
        :param bool italic: italic face (False)
        :param float alpha:  opacity level
        :param float angle:  anticlockwise rotation in degrees

        |buttons| |buttons.py|_
        """
        return addons.addButton(fnc, states, c, bc, pos, size, font, bold, italic, alpha, angle)

    def addCutterTool(self, actor):
        """Create handles to cut away parts of a mesh.

        |cutter| |cutter.py|_
        """
        return addons.addCutterTool(actor)

    def addIcon(self, iconActor, pos=3, size=0.08):
        """Add an inset icon mesh into the same renderer.

        :param pos: icon position in the range [1-4] indicating one of the 4 corners,
                    or it can be a tuple (x,y) as a fraction of the renderer size.
        :param float size: size of the square inset.

        |icon| |icon.py|_
        """
        return addons.addIcon(iconActor, pos, size)

    def addAxes(self, axtype=None, c=None):
        """Draw axes on scene. Available axes types:

        :param int axtype:

              - 0,  no axes,
              - 1,  draw three gray grid walls
              - 2,  show cartesian axes from (0,0,0)
              - 3,  show positive range of cartesian axes from (0,0,0)
              - 4,  show a triad at bottom left
              - 5,  show a cube at bottom left
              - 6,  mark the corners of the bounding box
              - 7,  draw a simple ruler at the bottom of the window
              - 8,  show the ``vtkCubeAxesActor`` object
              - 9,  show the bounding box outLine
              - 10, show three circles representing the maximum bounding box

        Axis type-1 can be fully customized by passing a dictionary ``axes=dict()`` where:

            - `xtitle`,            ['x'], x-axis title text.
            - `ytitle`,            ['y'], y-axis title text.
            - `ztitle`,            ['z'], z-axis title text.
            - `numberOfDivisions`,   [4], number of divisions on the shortest axis
            - `axesLineWidth`,       [1], width of the axes lines
            - `gridLineWidth`,       [1], width of the grid lines
            - `reorientShortTitle`, [True], titles shorter than 3 letters are placed horizontally
            - `originMarkerSize`, [0.01], draw a small cube on the axis where the origin is
            - `enableLastLabel`, [False], show last numeric label on axes
            - `titleDepth`,          [0], extrusion fractional depth of title text
            - `xyGrid`,           [True], show a gridded wall on plane xy
            - `yzGrid`,           [True], show a gridded wall on plane yz
            - `zxGrid`,          [False], show a gridded wall on plane zx
            - `zxGrid2`,         [False], show zx plane on opposite side of the bounding box
            - `xyPlaneColor`,   ['gray'], color of gridded plane
            - `xyGridColor`,    ['gray'], grid line color
            - `xyAlpha`,          [0.15], grid plane opacity
            - `showTicks`,        [True], show major ticks
            - `xTitlePosition`,   [0.32], title fractional positions along axis
            - `xTitleOffset`,     [0.05], title fractional offset distance from axis line
            - `xTitleJustify`, ["top-right"], title justification
            - `xTitleRotation`,      [0], add a rotation of the axis title
            - `xLineColor`,  [automatic], color of the x-axis
            - `xTitleColor`, [automatic], color of the axis title
            - `xTitleBackfaceColor`, [None],  color of axis title on its backface
            - `xTitleSize`,      [0.025], size of the axis title
            - `xHighlightZero`,   [True], draw a line highlighting zero position if in range
            - `xHighlightZeroColor`, [automatic], color of the line highlighting the zero position
            - `xTickRadius`,     [0.005], radius of the major ticks
            - `xTickThickness`, [0.0025], thickness of the major ticks along their axis
            - `xTickColor`,  [automatic], color of major ticks
            - `xMinorTicks`,         [1], number of minor ticks between two major ticks
            - `tipSize`,          [0.01], size of the arrow tip
            - `xLabelPrecision`,     [2], nr. of significative digits to be shown
            - `xLabelSize`,      [0.015], size of the numeric labels along axis
            - `xLabelOffset`,    [0.025], offset of numeric labels

            :Example:

                .. code-block:: python

                    from vtkplotter import Box, show
                    b = Box(pos=(0,0,0), length=80, width=90, height=70).alpha(0)

                    show(b, axes={ 'xtitle':'Some long variable [a.u.]',
                                   'numberOfDivisions':4,
                                   # ...
                                 }
                    )

        |customAxes| |customAxes.py|_
        """
        return addons.addAxes(axtype, c)

    def addLegend(self):
        return addons.addLegend()


    ##############################################################################
    def show(
        self,
        *actors, **options
#        at=None,
#        axes=None,
#        c=None,
#        alpha=None,
#        wire=False,
#        bc=None,
#        resetcam=True,
#        zoom=False,
#        interactive=None,
#        rate=None,
#        viewup="",
#        azimuth=0,
#        elevation=0,
#        roll=0,
#        interactorStyle=0,
#        q=False,
    ):
        """Render a list of actors.

        Allowed input objects are: ``filename``, ``vtkPolyData``, ``vtkActor``,
        ``vtkActor2D``, ``vtkImageActor``, ``vtkAssembly`` or ``vtkVolume``.

        If filename is given, its type is guessed based on its extension.
        Supported formats are:
        `vtu, vts, vtp, ply, obj, stl, 3ds, xml, neutral, gmsh, pcd, xyz, txt, byu,
        tif, slc, vti, mhd, png, jpg`.

        :param int at: number of the renderer to plot to, if more than one exists
        :param int axes: set the type of axes to be shown

              - 0,  no axes,
              - 1,  draw three customizable gray grid walls
              - 2,  show cartesian axes from (0,0,0)
              - 3,  show positive range of cartesian axes from (0,0,0)
              - 4,  show a triad at bottom left
              - 5,  show a cube at bottom left
              - 6,  mark the corners of the bounding box
              - 7,  draw a simple ruler at the bottom of the window
              - 8,  show the ``vtkCubeAxesActor`` object,
              - 9,  show the bounding box outLine,
              - 10, show three circles representing the maximum bounding box

        :param c:     surface color, in rgb, hex or name formats
        :param bc:    set a color for the internal surface face
        :param bool wire:  show actor in wireframe representation
        :param float azimuth/elevation/roll:  move camera accordingly
        :param str viewup:  either ['x', 'y', 'z'] or a vector to set vertical direction
        :param bool resetcam:  re-adjust camera position to fit objects
        :param dict camera: Camera parameters can further be specified with a dictionary assigned
           to the ``camera`` keyword (E.g. `show(camera={'pos':(1,2,3), 'thickness':1000,})`)

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
                (measured by holding a ruler up to your screen) and d is the distance from your
                eyes to the screen.

        :param bool interactive:  pause and interact with window (True)
            or continue execution (False)
        :param float rate:  maximum rate of `show()` in Hertz
        :param int interactorStyle: set the type of interaction

            - 0, TrackballCamera
            - 1, TrackballActor
            - 2, JoystickCamera
            - 3, Unicam
            - 4, Flight
            - 5, RubberBand3D
            - 6, RubberBandZoom

        :param bool q:  force program to quit after `show()` command returns.
        """
        at = options.pop("at", None)
        axes = options.pop("axes", None)
        resetcam = options.pop("resetcam", True)
        zoom = options.pop("zoom", False)
        interactive = options.pop("interactive", None)
        viewup = options.pop("viewup", "")
        azimuth = options.pop("azimuth", 0)
        elevation = options.pop("elevation", 0)
        roll = options.pop("roll", 0)
        camera = options.pop("camera", None)

        interactorStyle = options.pop("interactorStyle", 0)
        rate = options.pop("rate", None)
        q = options.pop("q", False)

        if self.offscreen:
            interactive = False
            self.interactive = False

        def scan(wannabeacts):
            scannedacts = []
            if not utils.isSequence(wannabeacts):
                wannabeacts = [wannabeacts]

            for a in wannabeacts:  # scan content of list

                if a is None:
                    pass

                elif isinstance(a, vtk.vtkActor):
                    scannedacts.append(a)
                    if hasattr(a, 'trail') and a.trail and not a.trail in self.actors:
                        scannedacts.append(a.trail)
                    if hasattr(a, 'shadow') and a.shadow and not a.shadow in self.actors:
                        scannedacts.append(a.shadow)

                elif isinstance(a, vtk.vtkAssembly):
                    scannedacts.append(a)
                    if a.trail and not a.trail in self.actors:
                        scannedacts.append(a.trail)

                elif isinstance(a, vtk.vtkActor2D):
                    if isinstance(a, vtk.vtkCornerAnnotation):
                        for a2 in settings.collectable_actors:
                            if isinstance(a2, vtk.vtkCornerAnnotation):
                                if at in a2.renderedAt: # remove old message
                                    self.remove(a2)
                    scannedacts.append(a)

                elif isinstance(a, vtk.vtkImageActor):
                    scannedacts.append(a)

                elif isinstance(a, vtk.vtkVolume):
                    if isinstance(a, Volume):
                        scannedacts.append(a)
                    else:
                        scannedacts.append(Volume(a.GetMapper().GetInput()))

                elif isinstance(a, vtk.vtkImageData):
                    scannedacts.append(Volume(a))

                elif isinstance(a, vtk.vtkPolyData):
                    scannedacts.append(Actor(a))

                elif isinstance(a, str):  # assume a filepath was given
                    out = vtkio.load(a)
                    scannedacts.append(out)

                elif isinstance(a, vtk.vtkUnstructuredGrid):
                    scannedacts.append(Actor(a))
                elif isinstance(a, vtk.vtkStructuredGrid):
                    scannedacts.append(Actor(a))
                elif isinstance(a, vtk.vtkRectilinearGrid):
                    scannedacts.append(Actor(a))

                elif isinstance(a, vtk.vtkMultiBlockDataSet):
                    for i in range(a.GetNumberOfBlocks()):
                        b =  a.GetBlock(i)
                        if isinstance(b, vtk.vtkPolyData):
                            scannedacts.append(Actor(b))
                        elif isinstance(b, vtk.vtkImageData):
                            scannedacts.append(Volume(b))

                elif "dolfin" in str(type(a)):  # assume a dolfin.Mesh object
                    from vtkplotter.dolfin import MeshActor
                    out = MeshActor(a)
                    scannedacts.append(out)

                elif "trimesh" in str(type(a)):
                    scannedacts.append(utils.trimesh2vtk(a))

                else:
                    colors.printc("~!? Cannot understand input in show():", type(a), c=1)
                    scannedacts.append(None)
            return scannedacts

        if len(actors) == 0:
            actors = None
        elif len(actors) == 1:
            actors = actors[0]
        else:
            actors = utils.flatten(actors)

        if actors is not None:
            self.actors = []
            actors2show = scan(actors)
            for a in actors2show:
                if a not in self.actors:
                    self.actors.append(a)
        else:
            actors2show = scan(self.actors)
            self.actors = list(actors2show)

        if axes is not None:
            self.axes = axes

        if settings.notebookBackend == 'k3d':
            import k3d # https://github.com/K3D-tools/K3D-jupyter

            actors2show2 = []
            for ia in actors2show:
                if isinstance(ia, vtk.vtkAssembly): #unpack assemblies
                    acass = ia.getActors()
                    actors2show2 += acass
                else:
                    actors2show2.append(ia)

            vbb, sizes, min_bns, max_bns = addons.computeVisibleBounds()
            kgrid = vbb[0], vbb[2], vbb[4], vbb[1], vbb[3], vbb[5]

            settings.notebook_plotter = k3d.plot(axes=[self.xtitle, self.ytitle, self.ztitle],
                                                 menu_visibility=True,
                                                 height=int(self.size[1]/2) )
            settings.notebook_plotter.grid = kgrid

            if not self.axes:
                settings.notebook_plotter.grid_visible = False

            for ia in actors2show2:
                kobj = None
                kcmap= None

                if isinstance(ia, Actor) and ia.N():

                    iap = ia.GetProperty()
                    krep = iap.GetRepresentation()

                    ia.computeNormals()
                    cpl = vtk.vtkCleanPolyData()
                    cpl.SetInputData(ia.polydata())
                    cpl.Update()
                    tf = vtk.vtkTriangleFilter()
                    tf.SetInputData(cpl.GetOutput())
                    tf.Update()
                    iapoly = tf.GetOutput()
                    #iapoly = ia.polydata()

                    mass = vtk.vtkMassProperties()
                    mass.SetGlobalWarningDisplay(0)
                    mass.SetInputData(iapoly)
                    mass.Update()
                    area = mass.GetSurfaceArea()

                    color_attribute = None
                    if ia.mapper.GetScalarVisibility():
                        vtkdata = iapoly.GetPointData()
                        vtkscals = vtkdata.GetScalars()

                        if vtkscals is None:
                            vtkdata = iapoly.GetCellData()
                            vtkscals = vtkdata.GetScalars()
                            if vtkscals is not None:
                                c2p = vtk.vtkCellDataToPointData()
                                c2p.SetInputData(iapoly)
                                c2p.Update()
                                iapoly = c2p.GetOutput()
                                vtkdata = iapoly.GetPointData()
                                vtkscals = vtkdata.GetScalars()

                        if vtkscals is not None:
                            if not vtkscals.GetName():
                                vtkscals.SetName('scalars')
                            scals_min, scals_max = ia.mapper.GetScalarRange()
                            color_attribute = (vtkscals.GetName(), scals_min, scals_max)
                            lut = ia.mapper.GetLookupTable()
                            lut.Build()
                            kcmap=[]
                            nlut = lut.GetNumberOfTableValues()
                            for i in range(nlut):
                                r,g,b,a = lut.GetTableValue(i)
                                kcmap += [i/nlut, r,g,b]

                    if area > 0:
                        name = None
                        if ia.filename:
                            name = os.path.basename(ia.filename)
                        kobj = k3d.vtk_poly_data(iapoly,
                                                 name=name,
                                                 color=colors.rgb2int(iap.GetColor()),
                                                 color_attribute=color_attribute,
                                                 color_map=kcmap,
                                                 opacity=iap.GetOpacity(),
                                                 wireframe=(krep==1))

                        if iap.GetInterpolation() == 0:
                            kobj.flat_shading = True

                    else:
                        kcols=[]
                        if color_attribute is not None:
                            scals = vtk_to_numpy(vtkscals)
                            kcols = k3d.helpers.map_colors(scals, kcmap,
                                                           [scals_min,scals_max]).astype(numpy.uint32)
                        sqsize = numpy.sqrt(numpy.dot(sizes, sizes))
                        if ia.NPoints() == ia.NCells():
                            kobj = k3d.points(ia.coordinates().astype(numpy.float32),
                                              color=colors.rgb2int(iap.GetColor()),
                                              colors=kcols,
                                              opacity=iap.GetOpacity(),
                                              shader="3d",
                                              point_size=iap.GetPointSize()*sqsize/400,
                                              #compression_level=9,
                                              )
                        else:
                            kobj = k3d.line(ia.coordinates().astype(numpy.float32),
                                            color=colors.rgb2int(iap.GetColor()),
                                            colors=kcols,
                                            opacity=iap.GetOpacity(),
                                            shader="thick",
                                            width=iap.GetLineWidth()*sqsize/1000,
                                            )

                    settings.notebook_plotter += kobj

                elif isinstance(ia, Volume):
                    kx, ky, kz = ia.dimensions()
                    arr = ia.getPointArray()
                    kimage = arr.reshape(-1, ky, kx)

                    colorTransferFunction = ia.GetProperty().GetRGBTransferFunction()
                    kcmap=[]
                    for i in range(256):
                        r,g,b = colorTransferFunction.GetColor(i/255)
                        kcmap += [i/255, r,g,b]

                    kobj = k3d.volume(kimage.astype(numpy.float32),
                                      color_map=kcmap,
                                      alpha_coef=5,
                                      bounds=ia.bounds() )
                    settings.notebook_plotter += kobj

                elif hasattr(ia, 'info') and 'formula' in ia.info.keys():
                    pos = (ia.GetPosition()[0],ia.GetPosition()[1])
                    kobj = k3d.text2d(ia.info['formula'], position=pos)
                    settings.notebook_plotter += kobj

            ###################################
            return settings.notebook_plotter
            ###################################

        elif settings.notebookBackend == 'panel' and hasattr(self, 'window') and self.window:
            import panel # https://panel.pyviz.org/reference/panes/VTK.html
            settings.notebook_plotter = panel.pane.VTK(self.window,
                                                       width=int(self.size[0]/2),
                                                       height=int(self.size[1]/2))
            ###################################
            return settings.notebook_plotter
            ###################################

        if not hasattr(self, 'window'):
            return

        if interactive is not None:
            self.interactive = interactive

        if at is None and len(self.renderers) > 1:
            # in case of multiple renderers a call to show w/o specifing
            # at which renderer will just render the whole thing and return
            if self.interactor:
                if zoom:
                    self.camera.Zoom(zoom)
                self.interactor.Render()
                if self.interactive:
                    self.interactor.Start()
                return

        if at is None:
            at = 0

        if at < len(self.renderers):
            self.renderer = self.renderers[at]
        else:
            colors.printc("~times Error in show(): wrong renderer index", at, c=1)
            return

        if self.qtWidget is not None:
            self.qtWidget.GetRenderWindow().AddRenderer(self.renderer)

        if not self.camera:
            if isinstance(camera, vtk.vtkCamera):
                self.camera = camera
            else:
                self.camera = self.renderer.GetActiveCamera()
        self.camera.SetParallelProjection(self.infinity)

        if self.sharecam:
            for r in self.renderers:
                r.SetActiveCamera(self.camera)

        if len(self.renderers) == 1:
            self.renderer.SetActiveCamera(self.camera)

        # rendering
        for ia in actors2show:  # add the actors that are not already in scene
            if ia:
                if isinstance(ia, vtk.vtkVolume):
                    self.renderer.AddVolume(ia)
                else:
                    self.renderer.AddActor(ia)
                if hasattr(ia, 'renderedAt'):
                    ia.renderedAt.add(at)
            else:
                colors.printc("~lightning Warning: Invalid actor in actors list, skip.", c=5)

        # remove the ones that are not in actors2show
        for ia in self.getActors(at):
            if ia not in actors2show:
                self.renderer.RemoveActor(ia)
                if hasattr(ia, 'renderedAt'):
                    ia.renderedAt.discard(at)

        for ia in self.getVolumes(at):
            if ia not in actors2show:
                self.renderer.RemoveActor(ia)
                if hasattr(ia, 'renderedAt'):
                    ia.renderedAt.discard(at)

        for c in self.scalarbars:
            self.renderer.RemoveActor(c)
            if hasattr(c, 'renderedAt'):
                c.renderedAt.discard(at)


        if self.axes is not None and not settings.notebookBackend:
            addons.addAxes()

        addons.addLegend()

        if self.showFrame and len(self.renderers) > 1:
            addons.addFrame()

        if resetcam or self.initializedIren == False:
            self.renderer.ResetCamera()

        if not self.initializedIren and self.interactor:
            self.initializedIren = True
            self.interactor.Initialize()
            self.interactor.RemoveObservers("CharEvent")

            if self.verbose and self.interactive:
                if not settings.notebookBackend:
                    docs.onelinetip()

        self.initializedPlotter = True

        if zoom:
            self.camera.Zoom(zoom)
        if azimuth:
            self.camera.Azimuth(azimuth)
        if elevation:
            self.camera.Elevation(elevation)
        if roll:
            self.camera.Roll(roll)

        if self._first_viewup and len(viewup):
            self._first_viewup = False # gets executed only once
            if viewup == "x":
                self.camera.SetViewUp([1, 0.001, 0])
            elif viewup == "y":
                self.camera.SetViewUp([0.001, 1, 0])
            elif viewup == "z":
                b =  self.renderer.ComputeVisiblePropBounds()
                self.camera.SetViewUp([0, 0.001, 1])
                cm = [(b[1]+b[0])/2, (b[3]+b[2])/2, (b[5]+b[4])/2]
                sz = numpy.array([(b[1]-b[0])*0.7, -(b[3]-b[2])*1.0, (b[5]-b[4])*1.2])
                self.camera.SetPosition(cm+2*sz)

        if camera is not None:
            cm_pos = camera.pop("pos", None)
            cm_focalPoint = camera.pop("focalPoint", None)
            cm_viewup = camera.pop("viewup", None)
            cm_distance = camera.pop("distance", None)
            cm_clippingRange = camera.pop("clippingRange", None)
            cm_parallelScale = camera.pop("parallelScale", None)
            cm_thickness = camera.pop("thickness", None)
            cm_viewAngle = camera.pop("viewAngle", None)
            if cm_pos is not None: self.camera.SetPosition(cm_pos)
            if cm_focalPoint is not None: self.camera.SetFocalPoint(cm_focalPoint)
            if cm_viewup is not None: self.camera.SetViewUp(cm_viewup)
            if cm_distance is not None: self.camera.SetDistance(cm_distance)
            if cm_clippingRange is not None: self.camera.SetClippingRange(cm_clippingRange)
            if cm_parallelScale is not None: self.camera.SetParallelScale(cm_parallelScale)
            if cm_thickness is not None: self.camera.SetThickness(cm_thickness)
            if cm_viewAngle is not None: self.camera.SetViewAngle(cm_viewAngle)

        if resetcam: self.renderer.ResetCameraClippingRange()

        self.window.Render()

        scbflag = False
        for a in self.actors:
            if (
                hasattr(a, "scalarbar")
                and a.scalarbar is not None
                and utils.isSequence(a.scalarbar)
            ):
                if len(a.scalarbar) == 5:  # addScalarBar
                    s1, s2, s3, s4, s5 = a.scalarbar
                    sb = addons.addScalarBar(a, s1, s2, s3, s4, s5)
                    scbflag = True
                    a.scalarbar = sb  # save scalarbar actor
                elif len(a.scalarbar) == 10:  # addScalarBar3D
                    s0, s1, s2, s3, s4, s5, s6, s7, s8 = a.scalarbar
                    sb = addons.addScalarBar3D(a, at, s0, s1, s2, s3, s4, s5, s6, s7, s8)
                    scbflag = True
                    a.scalarbar = sb  # save scalarbar actor
        if scbflag:
            self.window.Render()

        if settings.allowInteraction and not self.offscreen:
            self.allowInteraction()

        if settings.interactorStyle is not None:
            interactorStyle = settings.interactorStyle

        if interactorStyle == 0 or interactorStyle == "TrackballCamera":
            pass  # do nothing
        elif interactorStyle == 1 or interactorStyle == "TrackballActor":
            self.interactor.SetInteractorStyle(vtk.vtkInteractorStyleTrackballActor())
        elif interactorStyle == 2 or interactorStyle == "JoystickCamera":
            self.interactor.SetInteractorStyle(vtk.vtkInteractorStyleJoystickCamera())
        elif interactorStyle == 3 or interactorStyle == "Unicam":
            self.interactor.SetInteractorStyle(vtk.vtkInteractorStyleUnicam())
        elif interactorStyle == 4 or interactorStyle == "Flight":
            self.interactor.SetInteractorStyle(vtk.vtkInteractorStyleFlight())
        elif interactorStyle == 5 or interactorStyle == "RubberBand3D":
            self.interactor.SetInteractorStyle(vtk.vtkInteractorStyleRubberBand3D())
        elif interactorStyle == 6 or interactorStyle == "RubberBandZoom":
            self.interactor.SetInteractorStyle(vtk.vtkInteractorStyleRubberBandZoom())

        if  hasattr(self, 'interactor') and self.interactor and self.interactive:
            self.interactor.Start()

        if rate:
            if self.clock is None:  # set clock and limit rate
                self._clockt0 = time.time()
                self.clock = 0.0
            else:
                t = time.time() - self._clockt0
                elapsed = t - self.clock
                mint = 1.0 / rate
                if elapsed < mint:
                    time.sleep(mint - elapsed)
                self.clock = time.time() - self._clockt0

        if q:  # exit python
            if self.verbose:
                print("q flag set to True.  Exit python session.")
            sys.exit(0)

        return self


    def showInset(self, *actors, **options): #pos=3, size=0.1, c='r', draggable=True):
        """Add a draggable inset space into a renderer.

        :param pos: icon position in the range [1-4] indicating one of the 4 corners,
                    or it can be a tuple (x,y) as a fraction of the renderer size.
        :param float size: size of the square inset.
        :param bool draggable: if True the subrenderer space can be dragged around.

        |inset| |inset.py|_
        """
        pos = options.pop("pos", None)
        size = options.pop("size", 0.1)
        c = options.pop("c", 'r')
        draggable = options.pop("draggable", True)

        if not self.renderer:
            colors.printc("~lightningWarning: Use showInset() after first rendering the scene.", c=3)
            save_int = self.interactive
            self.show(interactive=0)
            self.interactive = save_int
        widget = vtk.vtkOrientationMarkerWidget()
        r,g,b = colors.getColor(c)
        widget.SetOutlineColor(r,g,b)
        if len(actors)==1:
            widget.SetOrientationMarker(actors[0])
        else:
            widget.SetOrientationMarker(Assembly(utils.flatten(actors)))
        widget.SetInteractor(self.interactor)
        if utils.isSequence(pos):
            widget.SetViewport(pos[0] - size, pos[1] - size, pos[0] + size, pos[1] + size)
        else:
            if pos < 2:
                widget.SetViewport(0, 1 - 2 * size, size * 2, 1)
            elif pos == 2:
                widget.SetViewport(1 - 2 * size, 1 - 2 * size, 1, 1)
            elif pos == 3:
                widget.SetViewport(0, 0, size * 2, size * 2)
            elif pos == 4:
                widget.SetViewport(1 - 2 * size, 0, 1, size * 2)
        widget.EnabledOn()
        widget.SetInteractive(draggable)
        self.widgets.append(widget)
        for a in actors:
            if a in self.actors:
                self.actors.remove(a)
        return widget

    def clear(self, actors=()):
        """Delete specified list of actors, by default delete all."""
        if not utils.isSequence(actors):
            actors = [actors]
        if len(actors):
            for a in actors:
                self.remove(a)
        else:
            for a in settings.collectable_actors:
                self.remove(a)
            settings.collectable_actors = []
            self.actors = []
            for a in self.getActors():
                self.renderer.RemoveActor(a)
            for a in self.getVolumes():
                self.renderer.RemoveVolume(a)
            for s in self.sliders:
                s.EnabledOff()
            for b in self.buttons:
                self.renderer.RemoveActor(b)
            for w in self.widgets:
                w.EnabledOff()
            for c in self.scalarbars:
                self.renderer.RemoveActor(c)

    def closeWindow(self):
        """Close the current or the input rendering window."""
        if hasattr(self, 'window') and self.window:
            self.window.Finalize()
            if hasattr(self, 'interactor') and self.interactor:
                self.interactor.TerminateApp()
                del self.window
                del self.interactor
#        if settings.notebook_plotter:
#            settings.notebook_plotter.close()
        return self

    def close(self):
        self.closeWindow()
        self.actors = []
        settings.collectable_actors = []
        return None


    #######################################################################
    def _mouseleft(self, iren, event):

        x, y = iren.GetEventPosition()
        #print('_mouseleft mouse at', x, y)

        renderer = iren.FindPokedRenderer(x, y)
        self.renderer = renderer

        picker = vtk.vtkPropPicker()
        picker.PickProp(x, y, renderer)
        clickedActor = picker.GetActor()

        # check if any button objects are clicked
        clickedActor2D = picker.GetActor2D()
        if clickedActor2D:
            for bt in self.buttons:
                if clickedActor2D == bt.actor:
                    bt.function()
                    break

        if not clickedActor:
            clickedActor = picker.GetAssembly()
        self.picked3d = picker.GetPickPosition()
        self.justremoved = None

        if not hasattr(clickedActor, "GetPickable") or not clickedActor.GetPickable():
            return
        self.clickedActor = clickedActor

        if self.mouseLeftClickFunction:
            self.mouseLeftClickFunction(clickedActor)


    def _mouseright(self, iren, event):

        x, y = iren.GetEventPosition()

        renderer = iren.FindPokedRenderer(x, y)
        self.renderer = renderer

        picker = vtk.vtkPropPicker()
        picker.PickProp(x, y, renderer)
        clickedActor = picker.GetActor()

        # check if any button objects were created
        clickedActor2D = picker.GetActor2D()
        if clickedActor2D:
            for bt in self.buttons:
                if clickedActor2D == bt.actor:
                    bt.function()
                    break

        if not clickedActor:
            clickedActor = picker.GetAssembly()
        self.picked3d = picker.GetPickPosition()

        if not hasattr(clickedActor, "GetPickable") or not clickedActor.GetPickable():
            return
        self.clickedActor = clickedActor

        if self.mouseRightClickFunction:
            self.mouseRightClickFunction(clickedActor)


    def _mousemiddle(self, iren, event):

        x, y = iren.GetEventPosition()

        renderer = iren.FindPokedRenderer(x, y)
        self.renderer = renderer

        picker = vtk.vtkPropPicker()
        picker.PickProp(x, y, renderer)
        clickedActor = picker.GetActor()

        # check if any button objects were created
        clickedActor2D = picker.GetActor2D()
        if clickedActor2D:
            for bt in self.buttons:
                if clickedActor2D == bt.actor:
                    bt.function()
                    break

        if not clickedActor:
            clickedActor = picker.GetAssembly()
        self.picked3d = picker.GetPickPosition()

        if not hasattr(clickedActor, "GetPickable") or not clickedActor.GetPickable():
            return
        self.clickedActor = clickedActor

        if self.mouseMiddleClickFunction:
            self.mouseMiddleClickFunction(self.clickedActor)


    def _keypress(self, iren, event):
        # qt creates and passes a vtkGenericRenderWindowInteractor

        key = iren.GetKeySym()
        #print('Pressed key:', key, [vp])

        if key in ["q", "Q", "space", "Return"]:
            iren.ExitCallback()
            return

        elif key == "Escape":
            sys.stdout.flush()
            settings.plotter_instance.closeWindow()

        elif key in ["F1", "Pause"]:
            sys.stdout.flush()
            colors.printc('\n[F1] Execution aborted. Exiting python now.')
            settings.plotter_instance.closeWindow()
            sys.exit(0)

        elif key == "m":
            if self.clickedActor in self.getActors():
                self.clickedActor.GetProperty().SetOpacity(0.02)
                bfp = self.clickedActor.GetBackfaceProperty()
                if bfp and hasattr(self.clickedActor, "_bfprop"):
                    self.clickedActor._bfprop = bfp  # save it
                    self.clickedActor.SetBackfaceProperty(None)
            else:
                for a in self.getActors():
                    if a.GetPickable():
                        a.GetProperty().SetOpacity(0.02)
                        bfp = a.GetBackfaceProperty()
                        if bfp and hasattr(a, "_bfprop"):
                            a._bfprop = bfp
                            a.SetBackfaceProperty(None)

        elif key == "comma":
            if self.clickedActor in self.getActors():
                ap = self.clickedActor.GetProperty()
                aal = max([ap.GetOpacity() * 0.75, 0.01])
                ap.SetOpacity(aal)
                bfp = self.clickedActor.GetBackfaceProperty()
                if bfp and hasattr(self.clickedActor, "_bfprop"):
                    self.clickedActor._bfprop = bfp
                    self.clickedActor.SetBackfaceProperty(None)
            else:
                for a in self.getActors():
                    if a.GetPickable():
                        ap = a.GetProperty()
                        aal = max([ap.GetOpacity() * 0.75, 0.01])
                        ap.SetOpacity(aal)
                        bfp = a.GetBackfaceProperty()
                        if bfp and hasattr(a, "_bfprop"):
                            a._bfprop = bfp
                            a.SetBackfaceProperty(None)

        elif key == "period":
            if self.clickedActor in self.getActors():
                ap = self.clickedActor.GetProperty()
                aal = min([ap.GetOpacity() * 1.25, 1.0])
                ap.SetOpacity(aal)
                if aal == 1 and hasattr(self.clickedActor, "_bfprop") and self.clickedActor._bfprop:
                    # put back
                    self.clickedActor.SetBackfaceProperty(self.clickedActor._bfprop)
            else:
                for a in self.getActors():
                    if a.GetPickable():
                        ap = a.GetProperty()
                        aal = min([ap.GetOpacity() * 1.25, 1.0])
                        ap.SetOpacity(aal)
                        if aal == 1 and hasattr(a, "_bfprop") and a._bfprop:
                            a.SetBackfaceProperty(a._bfprop)

        elif key == "slash":
            if self.clickedActor in self.getActors():
                self.clickedActor.GetProperty().SetOpacity(1)
                if hasattr(self.clickedActor, "_bfprop") and self.clickedActor._bfprop:
                    self.clickedActor.SetBackfaceProperty(self.clickedActor._bfprop)
            else:
                for a in self.getActors():
                    if a.GetPickable():
                        a.GetProperty().SetOpacity(1)
                        if hasattr(a, "_bfprop") and a._bfprop:
                            a.clickedActor.SetBackfaceProperty(a._bfprop)

        elif key == "P":
            if self.clickedActor in self.getActors():
                acts = [self.clickedActor]
            else:
                acts = self.getActors()
            for ia in acts:
                if ia.GetPickable():
                    try:
                        ps = ia.GetProperty().GetPointSize()
                        if ps > 1:
                            ia.GetProperty().SetPointSize(ps - 1)
                        ia.GetProperty().SetRepresentationToPoints()
                    except AttributeError:
                        pass

        elif key == "p":
            if self.clickedActor in self.getActors():
                acts = [self.clickedActor]
            else:
                acts = self.getActors()
            for ia in acts:
                if ia.GetPickable():
                    try:
                        ps = ia.GetProperty().GetPointSize()
                        ia.GetProperty().SetPointSize(ps + 2)
                        ia.GetProperty().SetRepresentationToPoints()
                    except AttributeError:
                        pass

        elif key == "w":
            if self.clickedActor and self.clickedActor in self.getActors():
                self.clickedActor.GetProperty().SetRepresentationToWireframe()
            else:
                for a in self.getActors():
                    if a and a.GetPickable():
                        if a.GetProperty().GetRepresentation() == 1:  # toggle
                            a.GetProperty().SetRepresentationToSurface()
                        else:
                            a.GetProperty().SetRepresentationToWireframe()

        elif key == "r":
            self.renderer.ResetCamera()

        #############################################################
        ### now intercept custom observer ###########################
        #############################################################
        if self.keyPressFunction:
            if key not in ["Shift_L", "Control_L", "Super_L", "Alt_L"]:
                if key not in ["Shift_R", "Control_R", "Super_R", "Alt_R"]:
                    self.verbose = False
                    self.keyPressFunction(key)
                    return

        if key == "h":
            from vtkplotter.docs import tips

            tips()
            return

        if key == "a":
            iren.ExitCallback()
            cur = iren.GetInteractorStyle()
            if isinstance(cur, vtk.vtkInteractorStyleTrackballCamera):
                print("\nInteractor style changed to TrackballActor")
                print("  you can now move and rotate individual meshes:")
                print("  press X twice to save the repositioned mesh,")
                print("  press 'a' to go back to normal style.")
                iren.SetInteractorStyle(vtk.vtkInteractorStyleTrackballActor())
            else:
                iren.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
            iren.Start()
            return

        if key == "j":
            iren.ExitCallback()
            cur = iren.GetInteractorStyle()
            if isinstance(cur, vtk.vtkInteractorStyleJoystickCamera):
                iren.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
            else:
                print("\nInteractor style changed to Joystick,", end="")
                print(" press j to go back to normal.")
                iren.SetInteractorStyle(vtk.vtkInteractorStyleJoystickCamera())
            iren.Start()
            return

        if key == "S":
            vtkio.screenshot("screenshot.png")
            colors.printc("~camera Saved rendering window as screenshot.png", c="blue")
            return

        if key == "C":
            cam = self.renderer.GetActiveCamera()
            print('\n### Example code to position this vtkCamera:')
            print('vp = vtkplotter.Plotter()\n...')
            print('vp.camera.SetPosition(',   [round(e, 3) for e in cam.GetPosition()],  ')')
            print('vp.camera.SetFocalPoint(', [round(e, 3) for e in cam.GetFocalPoint()], ')')
            print('vp.camera.SetViewUp(',     [round(e, 3) for e in cam.GetViewUp()], ')')
            print('vp.camera.SetDistance(',   round(cam.GetDistance(), 3), ')')
            print('vp.camera.SetClippingRange(', [round(e, 3) for e in cam.GetClippingRange()], ')')
            return

        if key == "s":
            if self.clickedActor and self.clickedActor in self.getActors():
                self.clickedActor.GetProperty().SetRepresentationToSurface()
            else:
                for a in self.getActors():
                    if a and a.GetPickable():
                        a.GetProperty().SetRepresentationToSurface()

        elif key == "V":
            if not (self.verbose):
                self._tips()
            self.verbose = not (self.verbose)
            print("Verbose: ", self.verbose)

        elif key == "1":
            self.icol += 1
            if self.clickedActor and hasattr(self.clickedActor, "GetProperty"):
                self.clickedActor.GetMapper().ScalarVisibilityOff()
                self.clickedActor.GetProperty().SetColor(colors.colors1[(self.icol) % 10])
            else:
                for i, ia in enumerate(self.getActors()):
                    if not ia.GetPickable():
                        continue
                    ia.GetProperty().SetColor(colors.colors1[(i + self.icol) % 10])
                    ia.GetMapper().ScalarVisibilityOff()
            addons.addLegend()

        elif key == "2":
            self.icol += 1
            if self.clickedActor and hasattr(self.clickedActor, "GetProperty"):
                self.clickedActor.GetMapper().ScalarVisibilityOff()
                self.clickedActor.GetProperty().SetColor(colors.colors2[(self.icol) % 10])
            else:
                for i, ia in enumerate(self.getActors()):
                    if not ia.GetPickable():
                        continue
                    ia.GetProperty().SetColor(colors.colors2[(i + self.icol) % 10])
                    ia.GetMapper().ScalarVisibilityOff()
            addons.addLegend()

        elif key == "3":
            c = colors.getColor("gold")
            acs = self.getActors()
            if len(acs) == 0: return
            alpha = 1.0 / len(acs)
            for ia in acs:
                if not ia.GetPickable():
                    continue
                ia.GetProperty().SetColor(c)
                ia.GetProperty().SetOpacity(alpha)
                ia.GetMapper().ScalarVisibilityOff()
            addons.addLegend()

        elif key == "4":
            for ia in self.getActors():
                if not ia.GetPickable():
                    continue
                if isinstance(ia, Actor):
                    iascals = ia.scalars()
                    if len(iascals):
                        stype, sname = iascals[ia._scals_idx]
                        if sname and "Normals" not in sname.lower(): # exclude normals
                            ia.scalars( ia._scals_idx )
                            ia.GetMapper().ScalarVisibilityOn()
                            #ia.GetMapper().SetScalarRange(ia.polydata().GetCellData().GetArray(sname).GetRange())
                            colors.printc("..active scalars set to:", sname,
                                          "\ttype:", stype, c='g', bold=0)
                        ia._scals_idx += 1
                        if ia._scals_idx >= len(iascals):
                            ia._scals_idx = 0
            addons.addLegend()

        elif key == "5":
            bgc = numpy.array(self.renderer.GetBackground()).sum() / 3
            if bgc <= 0:
                bgc = 0.223
            elif 0 < bgc < 1:
                bgc = 1
            else:
                bgc = 0
            self.renderer.SetBackground(bgc, bgc, bgc)

        elif "KP_" in key:  # change axes style
            asso = {
                    "KP_Insert":0, "KP_0":0,
                    "KP_End":1,    "KP_1":1,
                    "KP_Down":2,   "KP_2":2,
                    "KP_Next":3,   "KP_3":3,
                    "KP_Left":4,   "KP_4":4,
                    "KP_Begin":5,  "KP_5":5,
                    "KP_Right":6,  "KP_6":6,
                    "KP_Home":7,   "KP_7":7,
                    "KP_Up":8,     "KP_8":8,
                    "KP_Prior":9,  "KP_9":9,
                    }
            clickedr = self.renderers.index(self.renderer)
            if key in asso.keys():
                if self.axes_instances[clickedr]:
                    if hasattr(self.axes_instances[clickedr], "EnabledOff"):  # widget
                        self.axes_instances[clickedr].EnabledOff()
                    else:
                        self.renderer.RemoveActor(self.axes_instances[clickedr])
                    self.axes_instances[clickedr] = None
                addons.addAxes(axtype=asso[key], c=None)
                self.interactor.Render()

        elif key in ["k", "K"]:
            for a in self.getActors():
                ptdata = a.GetMapper().GetInput().GetPointData()
                cldata = a.GetMapper().GetInput().GetCellData()

                arrtypes = dict()
                arrtypes[vtk.VTK_UNSIGNED_CHAR] = "UNSIGNED_CHAR"
                arrtypes[vtk.VTK_UNSIGNED_INT] = "UNSIGNED_INT"
                arrtypes[vtk.VTK_FLOAT] = "FLOAT"
                arrtypes[vtk.VTK_DOUBLE] = "DOUBLE"
                foundarr = 0

                if key == "k":
                    for i in range(ptdata.GetNumberOfArrays()):
                        name = ptdata.GetArrayName(i)
                        if name == "Normals":
                            continue
                        ptdata.SetActiveScalars(name)
                        foundarr = 1
                    if not foundarr:
                        print("No vtkArray is associated to points", end="")
                        if hasattr(a, "_legend"):
                            print(" for actor:", a._legend)
                        else:
                            print()

                if key == "K":
                    for i in range(cldata.GetNumberOfArrays()):
                        name = cldata.GetArrayName(i)
                        if name == "Normals":
                            continue
                        cldata.SetActiveScalars(name)
                        foundarr = 1
                    if not foundarr:
                        print("No vtkArray is associated to cells", end="")
                        if hasattr(a, "_legend"):
                            print(" for actor:", a._legend)
                        else:
                            print()

                a.GetMapper().ScalarVisibilityOn()

        elif key == "l":
            if self.clickedActor in self.getActors():
                acts = [self.clickedActor]
            else:
                acts = self.getActors()
            for ia in acts:
                if not ia.GetPickable():
                    continue
                try:
                    ev = ia.GetProperty().GetEdgeVisibility()
                    ia.GetProperty().SetEdgeVisibility(not ev)
                    ia.GetProperty().SetRepresentationToSurface()
                    ia.GetProperty().SetLineWidth(0.1)
                except AttributeError:
                    pass

        elif key == "n":  # show normals to an actor
            from vtkplotter.analysis import normalLines

            if self.clickedActor in self.getActors():
                if self.clickedActor.GetPickable():
                    self.renderer.AddActor(normalLines(self.clickedActor))
                    iren.Render()
            else:
                print("Click an actor and press n to add normals.")


        elif key == "x":
            if self.justremoved is None:
                if self.clickedActor in self.getActors() or isinstance(self.clickedActor, vtk.vtkAssembly):
                    self.justremoved = self.clickedActor
                    self.renderer.RemoveActor(self.clickedActor)
                if hasattr(self.clickedActor, '_legend') and self.clickedActor._legend:
                    print('...removing actor: ' +
                          str(self.clickedActor._legend)+', press x to put it back')
                else:
                    print("Click an actor and press x to toggle it.")
            else:
                self.renderer.AddActor(self.justremoved)
                self.renderer.Render()
                self.justremoved = None
            addons.addLegend()

        elif key == "X":
            if self.clickedActor:
                if not self.cutterWidget:
                    addons.addCutterTool(self.clickedActor)
                else:
                    fname = "clipped.vtk"
                    confilter = vtk.vtkPolyDataConnectivityFilter()
                    if isinstance(self.clickedActor, vtk.vtkActor):
                        confilter.SetInputData(self.clickedActor.GetMapper().GetInput())
                    elif isinstance(self.clickedActor, vtk.vtkAssembly):
                        act = self.clickedActor.getActors()[0]
                        confilter.SetInputData(act.GetMapper().GetInput())
                    else:
                        confilter.SetInputData(self.clickedActor.polydata(True))
                    confilter.SetExtractionModeToLargestRegion()
                    confilter.Update()
                    cpd = vtk.vtkCleanPolyData()
                    cpd.SetInputData(confilter.GetOutput())
                    cpd.Update()
                    w = vtk.vtkPolyDataWriter()
                    w.SetInputData(cpd.GetOutput())
                    w.SetFileName(fname)
                    w.Write()
                    colors.printc("~save Saved file:", fname, c="m")
                    self.cutterWidget.Off()
                    self.cutterWidget = None
            else:
                for a in self.actors:
                    if isinstance(a, vtk.vtkVolume):
                        addons.addCutterTool(a)
                        return

                colors.printc("Click an actor and press X to open the cutter box widget.", c=4)

        elif key == "i":  # print info
            if self.clickedActor:
                utils.printInfo(self.clickedActor)
            else:
                utils.printInfo(self)

        if iren:
            iren.Render()

