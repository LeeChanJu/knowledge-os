import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import Site from "./docs/Site";
import type { Architecture } from "./model";
import "./style.css";

const target = document.getElementById("root")!;
target.textContent = "Loading architecture…";
import("../data/architecture.json")
  .then(({ default: data }) => {
    createRoot(target).render(
      <StrictMode>
        <Site data={data as unknown as Architecture} />
      </StrictMode>,
    );
  })
  .catch(() => {
    target.textContent =
      "Could not load this documentation snapshot. Reload the page or restart the Explorer.";
  });
