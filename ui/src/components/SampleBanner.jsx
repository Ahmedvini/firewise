// Backwards-compatible alias of the design-system Notice.
// Without children it renders nothing: the generic provenance message now lives once in the app footer.
import { Notice } from "./ui.jsx";

export default function SampleBanner({ children, danger = false }) {
  if (!children) return null;
  return <Notice tone={danger ? "danger" : "warn"}>{children}</Notice>;
}
