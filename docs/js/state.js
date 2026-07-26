// Mietspiegel Berlin — shared state (ES module)
export const DATA = 'data/processed/';

export let districts = [];
export let districtGeo = null;
export let map;
export let heatLayer = null;
export let berlinLayer = null;
export let districtLabels = [];

export let immoMean = 0;
export let immoStd = 0;
export let immoGrids = [];

export let zensusMode = false;
export let zensusMean = 0;
export let zensusStd = 0;
export let zensusCells = [];

export let berlinMietspiegel = null;
export let cmpData = null;

export let clickCell = null;
export let clickLat = null;
export let clickLng = null;
export let clickDistrict = null;
export let clickThreshold = 0;

export let cardDistrict = null;

export let suggestTimer = null;
export let suggestIdx = -1;
export let suggestResults = [];
