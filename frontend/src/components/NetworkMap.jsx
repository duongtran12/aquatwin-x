import { useEffect, useRef } from "react";
import cytoscape from "cytoscape";


function NetworkMap({ elements, selectedPipe, nodeStates, onSelectPipe }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || !elements) return undefined;

    const nodes = elements.nodes.map((node) => ({
      data: {
        id: node.id,
        label: node.id,
        type: node.type,
        state: nodeStates[node.id] || "normal",
      },
      position: { x: node.x, y: -node.y },
    }));
    const links = elements.links.map((link) => ({
      data: {
        id: link.id,
        label: link.id,
        source: link.source,
        target: link.target,
        selected: link.id === selectedPipe ? "yes" : "no",
      },
    }));

    const instance = cytoscape({
      container: containerRef.current,
      elements: [...nodes, ...links],
      layout: { name: "preset", fit: true, padding: 52 },
      minZoom: 0.55,
      maxZoom: 2.5,
      style: [
        {
          selector: "node",
          style: {
            width: 30,
            height: 30,
            "background-color": "#1b8195",
            "border-width": 3,
            "border-color": "#8ce8ef",
            label: "data(label)",
            color: "#dffbff",
            "font-size": 11,
            "font-weight": 700,
            "text-valign": "bottom",
            "text-margin-y": 8,
          },
        },
        {
          selector: 'node[type = "reservoir"]',
          style: {
            shape: "diamond",
            width: 42,
            height: 42,
            "background-color": "#54d1b5",
            "border-color": "#c3fff0",
          },
        },
        {
          selector: 'node[state = "affected"]',
          style: {
            "background-color": "#f26b52",
            "border-color": "#ffd0c5",
          },
        },
        {
          selector: "edge",
          style: {
            width: 6,
            "line-color": "#2e6475",
            "curve-style": "bezier",
            label: "data(label)",
            color: "#779aaa",
            "font-size": 9,
            "text-background-color": "#071a24",
            "text-background-opacity": 0.9,
            "text-background-padding": 3,
          },
        },
        {
          selector: 'edge[selected = "yes"]',
          style: {
            width: 9,
            "line-color": "#ffb95c",
            color: "#ffd99a",
          },
        },
      ],
    });

    instance.on("tap", "edge", (event) => {
      onSelectPipe(event.target.id());
    });
    return () => instance.destroy();
  }, [elements, selectedPipe, nodeStates, onSelectPipe]);

  return <div className="network-map" ref={containerRef} />;
}


export default NetworkMap;

