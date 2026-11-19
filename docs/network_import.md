# Importing EPANET networks

AquaTwin-X accepts EPANET `.inp` files from the dashboard. Select **Import EPANET .inp** in the top-right network controls, then choose a file up to 5 MB.

## Validation

An imported network must:

- use a UTF-8 compatible text encoding;
- contain at least two nodes and one pipe;
- contain at least one reservoir or tank;
- use unique node and link IDs;
- reference existing nodes from every pipe endpoint.

Built-in networks cannot be replaced. Uploading another file with the same normalized name returns a conflict so existing experiment evidence remains reproducible.

## Generated valve layer

The importer creates two virtual isolation valves for every pipe, one at each endpoint. This makes the network immediately available to manual what-if recovery, exhaustive search and the Genetic Algorithm. The generated layer is an analytical assumption and should be replaced with surveyed valve data before operational use.

## Persistence

Uploaded files are stored in `data/networks`, and generated valve registries are stored in `data/valves`. Both directories are part of the Docker `data` volume, so imported networks remain available after containers restart. Runtime files are ignored by Git.

An uploaded network can be removed with the **Delete** button beside the importer. AquaTwin-X requires confirmation, removes its generated valve registry and switches back to the built-in demo network. Built-in networks are protected from deletion. Existing run history and experiment archives are intentionally retained as immutable evidence.

Networks without coordinates are displayed with an automatic graph layout. Networks with an EPANET `[COORDINATES]` section preserve their supplied positions.
