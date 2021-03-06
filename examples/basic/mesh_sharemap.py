"""
How to share the same color map
across different meshes.
"""
from vtkplotter import load, Text, show, datadir


#####################################
man1 = load(datadir+"man.vtk")
scals = man1.coordinates()[:, 2] * 5 + 27  # pick z coordinates [18->34]

man1.pointColors(scals, cmap="jet", vmin=18, vmax=44)

#####################################
man2 = load(datadir+"man.vtk")
scals = man2.coordinates()[:, 2] * 5 + 37  # pick z coordinates [28->44]

man2.pointColors(scals, cmap="jet", vmin=18, vmax=44)

show([[man1, Text(__doc__)], man2], N=2, elevation=-40)
