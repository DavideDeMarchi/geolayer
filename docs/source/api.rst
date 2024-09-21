API
===


The geolayer library consists of two classes:

**rasterlayer** (see :py:class:`rasterlayer`) is the class dedicated to the display of raster datasets (.tif, .vrt, .nc, and all other raster formats managed by the GDAL library)

**vectorlayer** (see :py:class:`vectorlayer`) is the class that enables the display of shapefiles, geopackage, POSTGIS queries and WKT strings on a ipyleaflet Map


.. image:: figures/line.png


rasterlayer
-----------

.. automodule:: rasterlayer
    :members:
    :member-order: bysource
    
    
.. image:: figures/line.png


vectorlayer
-----------

.. tip::            
    The chapter :ref:`symbol-format-help` contains a guide on how symbology can be defined for vector datasets display. To visually edit symbols for vector datasets display, please use the `Symbol Editor <https://geolayer.azurewebsites.net>`_ described in chapter :ref:`symbol-editor-help`.


.. automodule:: vectorlayer
    :members:
    :member-order: bysource
