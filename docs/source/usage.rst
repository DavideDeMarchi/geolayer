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

    Notes on symbology:

    A symbol is a list of lists of items each having 3 elements: [SymbolizerName, KeyName, Value]
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
       vlayer.symbologyAdd(symbol=symbol)                              # Apply symbol to all features of the vectorlayer
       vlayer.symbologyAdd(rule="[CNTR_CODE] = 'IT'", symbol=symbol)   # Apply symbol only to features that are filtered by the rule on attributes
                                                                       # See https://github.com/mapnik/mapnik/wiki/Filter for help on filter sintax
       m.add(vlayer.tileLayer())


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

