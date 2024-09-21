API
===


The geolayer library consists of two classes:

**rasterlayer** is the class dedicated to the display of raster datasets (.tif, .vrt, .nc, and all other raster formats managed by the GDAL library)

**vectorlayer** is the class that enables the display of shapefiles, geopackage, POSTGIS queries and WKT strings on a ipyleaflet Map


.. image:: figures/line.png


rasterlayer
-----------

.. automodule:: rasterlayer
    :members:
    
    
.. image:: figures/line.png


vectorlayer
-----------

.. automodule:: vectorlayer
    :members:

        
.. tip::
    Always pass a valid extents string, since this will make the display much faster in most cases.

.. tip::            
    To visually edit symbols, please use the `Symbol Editor <https://geolayer.azurewebsites.net>`_ described in chapter :ref:`symbol-editor-help`.
