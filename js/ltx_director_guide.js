import { app } from "../../scripts/app.js";

// Geekatplay Director Guide is a pure pass-through processor node.
// All configuration (images, insert frames, strengths) comes from
// the guide_data output of Geekatplay Timeline Director.
// No dynamic widgets or sync logic needed.
app.registerExtension({
    name: "Comfy.GAPDirectorGuide",
    async nodeCreated(node) {
        if (node.comfyClass !== "GAPDirectorGuide") return;
        // Nothing to initialize — the node has no configurable widgets.
    },
});