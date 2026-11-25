YOUR SCOPE: `search` itself and every READ operation (kind "read" in `search` with no arguments).
For each read with a plain path (a graph file or a GET route), fetch the plain path with curl and
compare. Use a mix of targets: tutorial, erdos-883, erdos-257, erdos-1094 and one bulk-loaded
target with no work on it. Test search with at least ten realistic queries and note where the
right operation is not first.
