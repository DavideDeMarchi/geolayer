Usage
=====

.. _installation:

Installation
------------

geolayer cannot be installed autonomously. It is already pre-installed inside the JEO-lab docker images of the BDAP platform


Display raster datasets
-----------------------


Display vector datasets
-----------------------


.. note::

    Vector symbology format:

    Inside BDAP, vector datasets are rendered using a dynamic tile server that converts vector features into raster tiles using the `Mapnik library <https://mapnik.org/>`_


    In geolayer, a symbol is a list of lists of items each having 3 elements: [SymbolizerName, KeyName, Value].

    Each list inside the symbol is mapped into a style (from style0 to style9), thus allowing for overlapped symbols

    Example:

    .. code-block:: console

        symbol = [
                    [
                       ["PolygonSymbolizer", "fill", '#ff0000'],
                       ["PolygonSymbolizer", "fill-opacity", 0.3],
                       ["LineSymbolizer", "stroke", "#010000"],
                       ["LineSymbolizer", "stroke-width", 2.0]
                    ]
        ]

    Example on how to manage symbology:

    .. code-block:: console

       vlayer = vectorlayer.file('path to a .shp file', epsg=4326)
       vlayer.symbologyClear()

       # Apply symbol to all features of the vectorlayer
       vlayer.symbologyAdd(symbol=symbol)

       # Apply symbol only to features that are filtered by the rule on attributes
       vlayer.symbologyAdd(rule="[CNTR_CODE] = 'IT'", symbol=symbol)

       m.add(vlayer.tileLayer())

    For a complete guide of the mapnik filer syntax, see the `Mapnik Filter syntax page <https://github.com/mapnik/mapnik/wiki/Filter>`_

    The static methos vectorlayer.symbolChange can be used to change a parametric symbol

    Example:

    .. code-block:: console

        symbol = [
                    [
                       ["PolygonSymbolizer", "fill", 'FILL-COLOR'],
                       ["PolygonSymbolizer", "fill-opacity", 0.3],
                       ["LineSymbolizer", "stroke", "#010000"],
                       ["LineSymbolizer", "stroke-width", 2.0]
                    ]
        ]

        s = vectorlayer.symbolChange(fillColor='red')



Create symbols for vector datasets display
------------------------------------------

To help users of the geolayer library to create symbols for their vector datasets display, an online tool was developed and deployed on the Microsoft Azure Cloud: `the Symbol Editor <https://geolayer.azurewebsites.net/>`_

Here is a screenshot of the tool:

.. image:: ./figures/SymbolEditor.png


