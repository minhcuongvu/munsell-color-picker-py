from krita import DockWidgetFactory, DockWidgetFactoryBase
from .MunsellColorPicker import DockerTemplate

DOCKER_ID = 'MunsellColorPicker'
instance = Krita.instance()
dock_widget_factory = DockWidgetFactory(DOCKER_ID,
DockWidgetFactoryBase.DockRight,
DockerTemplate)

instance.addDockWidgetFactory(dock_widget_factory)