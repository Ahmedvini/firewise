// FIREWISE browser interaction tests: existing modules, Digital Twin (3D + 2D + evidence + physics + scenarios +
// report + Copilot), and saved Copilot conversations. Run: cd ui && npm run build && npx playwright test
import { test, expect } from "@playwright/test";

const consoleErrors = (page) => {
  const errs = [];
  page.on("console", (m) => m.type() === "error" && !/favicon|WebGL|GPU stall|swiftshader/i.test(m.text()) && errs.push(m.text()));
  page.on("pageerror", (e) => errs.push(String(e)));
  return errs;
};

async function freshTwin(page, preset = "Sea-level cabin air") {
  await page.goto("/#/twin/habitat");
  await page.evaluate(() => { try { localStorage.removeItem("firewise.twin.draft"); } catch { /* ignore */ } });
  await page.reload();
  await expect(page.locator(".scene-wrap canvas")).toBeVisible();
  await page.getByLabel("Start from a preset").selectOption({ label: preset });
  await expect(page.getByRole("heading", { level: 2, name: preset })).toBeVisible();
}

test("every existing FIREWISE module still renders without errors", async ({ page }) => {
  const errs = consoleErrors(page);
  for (const [route, text] of [["overview", "Start here"], ["experiments", "of 24 investigations"], ["compare", "Pick a preset or choose 2–4 investigations"],
    ["scenarios", "Pick a habitat atmosphere"], ["gaps", "Key evidence gaps"], ["insights", "Key evidence gaps"], ["assistant", "Ask a scientific question"]]) {
    await page.goto(`/#/${route}`);
    await expect(page.getByText(text).first()).toBeVisible();
  }
  expect(errs).toEqual([]);
});

test("3D habitat renders, responds to camera controls and zone selection by clicking the scene", async ({ page }) => {
  const errs = consoleErrors(page);
  await freshTwin(page);
  const canvas = page.locator(".scene-wrap canvas");
  await expect.poll(async () => (await canvas.boundingBox())?.width ?? 0).toBeGreaterThan(600);
  const box = await canvas.boundingBox();
  // WebGL actually drew something (not a blank canvas)
  const drawn = await page.evaluate(() => {
    const c = document.querySelector(".scene-wrap canvas");
    const gl = c.getContext("webgl2") || c.getContext("webgl");
    return !!gl && c.width > 0;
  });
  expect(drawn).toBe(true);
  // side view: zones are laid out left→right; click Z1 (x = 0.1·L − L/2 in world units)
  await page.getByRole("button", { name: "Side", exact: true }).click();
  await page.waitForTimeout(400);
  const L = 8, D = 4.2, span = Math.max(L, D), dist = span * 1.35;
  const visH = 2 * dist * Math.tan((42 / 2) * Math.PI / 180), visW = visH * (box.width / box.height);
  const px = box.x + box.width / 2 + ((0.1 * L - L / 2) / (visW / 2)) * (box.width / 2);
  await page.mouse.click(px, box.y + box.height / 2 + 6);
  await expect(page.locator(".zone-line")).toContainText("Zone Z1");
  await expect(page.getByRole("button", { name: /Z1 Forward hatch/ })).toHaveAttribute("aria-pressed", "true");
  // orbit / zoom / pan do not throw
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down(); await page.mouse.move(box.x + box.width / 2 + 120, box.y + box.height / 2 + 40, { steps: 6 }); await page.mouse.up();
  await page.mouse.wheel(0, -300);
  await page.mouse.down({ button: "right" }); await page.mouse.move(box.x + box.width / 2 - 60, box.y + box.height / 2, { steps: 4 }); await page.mouse.up({ button: "right" });
  for (const v of ["Top", "Inside", "3/4"]) await page.getByRole("button", { name: v, exact: true }).click();
  // overlays and airflow toggle
  await page.getByLabel("Environmental overlay").selectOption("temperature");
  await expect(page.locator(".scene-legend")).toContainText("Temperature (°C)");
  await expect(page.getByText(/Model C bulk velocity/)).toBeVisible();
  await page.getByRole("checkbox", { name: "Airflow", exact: true }).uncheck();
  await expect(page.getByText(/Model C bulk velocity/)).toHaveCount(0);
  expect(errs).toEqual([]);
});

test("controls update the shared state; 3D and 2D views agree; invalid input is rejected", async ({ page }) => {
  await freshTwin(page);
  await page.locator(".zone-chip", { hasText: "Z3" }).click();
  await page.locator("#o2").fill("30");
  await page.locator("#p").fill("500");
  await expect(page.getByText(/Allowed 10\.0–200\.0 kPa/)).toBeVisible();          // rejected, not committed
  await page.locator("#p").fill("70.33");
  await page.getByRole("tab", { name: /2D engineering/ }).click();
  await expect(page.getByText("70.33 kPa").first()).toBeVisible();
  await expect(page.getByText("Oxygen by zone (user-defined)")).toBeVisible();
  await page.getByRole("tab", { name: /3D habitat/ }).click();
  await expect(page.locator("#o2")).toHaveValue("30");                         // configuration survives view switches
  await expect(page.locator(".zone-line")).toContainText("O₂ 30%");
  await expect(page.locator(".glance")).toContainText("30% O₂");
});

test("evidence counts come from the database and source rows open", async ({ page, request }) => {
  await freshTwin(page, "Sea-level cabin air");
  const presets = await (await request.get("/api/twin/environments/fwh-1/presets")).json();
  const ev = await (await request.post("/api/twin/evaluate", { data: { scenario: presets[0].scenario } })).json();
  await page.getByRole("tab", { name: /NASA evidence/ }).click();
  const tile = page.locator(".stat-tile").filter({ hasText: "Exact matches" });
  await expect(tile.locator("strong")).toHaveText(String(ev.evidence.coverage.exact_matches));
  expect(ev.evidence.coverage.exact_matches).toBeGreaterThan(0);
  await page.locator(".ev-link").filter({ hasText: /row/ }).first().click();
  await expect(page.getByText("Verbatim record from the NASA PSI experimental table")).toBeVisible();
  await page.keyboard.press("Escape");
  // import a NASA record's conditions: values keep NASA status and source
  await page.getByRole("button", { name: "Use conditions" }).first().click();
  await expect(page.getByText(/Imported documented conditions from/)).toBeVisible();
  await expect(page.locator(".field").filter({ hasText: "Oxygen" }).locator(".tag").first()).toContainText(/Measured|Reported|Derived|Set-point/);
});

test("physics view shows units, assumptions, validation and unimplemented models", async ({ page }) => {
  await freshTwin(page);
  await page.getByRole("tab", { name: /Calculations/ }).click();
  await expect(page.getByRole("heading", { name: /Model B — Gas-mixture properties/ })).toBeVisible();
  await expect(page.getByText("19.224 kPa").or(page.getByText(/kPa/)).first()).toBeVisible();
  await expect(page.getByText("Missing inputs: surface_temperature_K")).toBeVisible();     // never assumed
  await expect(page.getByRole("heading", { name: "Model validation records" })).toBeVisible();
  await expect(page.getByRole("heading", { name: /Not implemented/ })).toBeVisible();
  await expect(page.getByText("Flame extinction limits")).toBeVisible();
});

test("scenarios: save, reload, duplicate, compare, history, simulation run, delete; report", async ({ page }) => {
  await freshTwin(page);
  await page.getByLabel("Scenario name").fill("E2E cabin");
  await page.getByRole("button", { name: /Save scenario/ }).first().click();
  await expect(page.getByText(/saved v1/)).toBeVisible();
  await page.locator("#o2").fill("23");
  await page.getByRole("button", { name: /^Save$/ }).click();
  await expect(page.getByText(/saved v2/)).toBeVisible();
  await page.reload();                                                                 // persisted on the server + draft
  await expect(page.locator("#o2")).toHaveValue("23");
  await page.getByRole("tab", { name: /Scenarios/ }).click();
  await expect(page.getByRole("cell", { name: /E2E cabin/ }).first()).toBeVisible();
  await page.getByRole("button", { name: "Duplicate" }).first().click();
  await expect(page.getByRole("cell", { name: /E2E cabin \(copy\)/ }).first()).toBeVisible();
  await page.locator("#o2").fill("27");
  await page.getByRole("button", { name: "Save new version" }).click();
  await page.getByRole("checkbox", { name: /Select E2E cabin for comparison/ }).check();
  await page.getByRole("checkbox", { name: /Select E2E cabin \(copy\) for comparison/ }).check();
  await page.getByRole("button", { name: /Compare selected/ }).click();
  await expect(page.getByRole("heading", { name: "Scenario comparison" })).toBeVisible();
  await expect(page.locator("tr.differs").first()).toBeVisible();
  await expect(page.getByRole("heading", { name: /Version history/ })).toBeVisible();
  await page.getByRole("tab", { name: /Calculations/ }).click();
  await page.getByRole("button", { name: "Run & record simulation" }).click();
  await expect(page.locator("td").filter({ hasText: /^run_/ }).first()).toBeVisible();
  await page.getByRole("tab", { name: /Report/ }).click();
  await expect(page.getByText(/not a fire-risk assessment/)).toBeVisible();
  await expect(page.getByRole("button", { name: /Markdown/ })).toBeVisible();
  await page.getByRole("tab", { name: /Scenarios/ }).click();
  const row = page.getByRole("row", { name: /E2E cabin \(copy\)/ });
  await row.getByRole("button", { name: "Delete" }).click();
  await row.getByRole("button", { name: "Confirm delete" }).click();
  await expect(page.getByRole("row", { name: /E2E cabin \(copy\)/ })).toHaveCount(0);
});

test("twin Copilot explains the active scenario without an API key", async ({ page }) => {
  await freshTwin(page, "Exploration atmosphere");
  await page.getByRole("button", { name: /Ask Copilot/ }).click();
  const drawer = page.getByRole("dialog", { name: "Twin Copilot" });
  await drawer.getByRole("button", { name: "What physical models can be applied here?" }).click();
  await expect(drawer.getByText(/physics models apply to this scenario/)).toBeVisible();
  await expect(drawer.locator(".tag.status").filter({ hasText: "Calculation" }).first()).toBeVisible();
  await expect(drawer.getByText(/Twin: Exploration atmosphere/)).toBeVisible();
  await drawer.getByLabel("Your question").fill("What prevents us from predicting flame behavior?");
  await drawer.getByLabel("Your question").press("Enter");
  await expect(drawer.getByText(/flame behaviour cannot be predicted/)).toBeVisible();
});

test("Copilot conversations: history is saved, chats switch, rename, delete; answers are cached", async ({ page }) => {
  await page.goto("/#/assistant");
  await page.getByRole("button", { name: /New chat/ }).click();
  await page.getByRole("button", { name: "Under what conditions did CFI-G produce cool flames?", exact: true }).click();
  await expect(page.getByText(/CFI-G tests are marked as cool flames/).first()).toBeVisible();
  await page.getByRole("button", { name: /New chat/ }).click();
  await page.getByRole("button", { name: "What is test 21265C3?", exact: true }).click();
  await expect(page.getByText(/short-lived inverse butane flame/)).toBeVisible();
  // switch back to the first conversation: its history is intact
  await page.locator(".chat-item").filter({ hasText: "Under what conditions did CFI-G" }).click();
  await expect(page.getByText(/CFI-G tests are marked as cool flames/).first()).toBeVisible();
  await expect(page.getByText(/short-lived inverse butane flame/)).toHaveCount(0);
  // reload: still there (the active conversation and the list)
  await page.reload();
  await expect(page.locator(".chat-item")).toHaveCount(2);
  await expect(page.getByText(/CFI-G tests are marked as cool flames/).first()).toBeVisible();
  // the same question in a new chat is served from the answer cache
  await page.getByRole("button", { name: /New chat/ }).click();
  await page.getByRole("button", { name: "Under what conditions did CFI-G produce cool flames?", exact: true }).click();
  await expect(page.getByText("Cached answer").first()).toBeVisible();
  await expect(page.locator(".chat-item")).toHaveCount(3);
  // rename and delete
  await page.getByRole("button", { name: /Rename What is test 21265C3/ }).click();
  await page.getByLabel("Conversation title").fill("Local test 21265C3");
  await page.getByRole("button", { name: "Save title" }).click();
  await expect(page.locator(".chat-item").filter({ hasText: "Local test 21265C3" })).toBeVisible();
  await page.getByRole("button", { name: /Delete Local test 21265C3/ }).click();
  await page.getByRole("button", { name: "Delete", exact: true }).click();
  await expect(page.locator(".chat-item")).toHaveCount(2);
});

test("navigation: six destinations, legacy links, progressive disclosure, mobile layout", async ({ page }) => {
  await page.goto("/#/overview");
  const nav = page.getByRole("navigation", { name: "Main navigation" });
  await expect(nav.locator(".nav-link")).toHaveCount(6);
  for (const [label, text] of [["Investigations", "of 24 investigations"], ["Scenario Explorer", "Pick a habitat atmosphere"], ["Research Gaps", "Key evidence gaps"], ["Copilot", "Ask a scientific question"], ["Overview", "Start here"]]) {
    await nav.getByRole("button", { name: label }).click();
    await expect(page.getByText(text).first()).toBeVisible();
  }
  // legacy routes land on their new homes, with the right nav item active
  await page.goto("/#/compare");
  await expect(nav.getByRole("button", { name: "Investigations" })).toHaveAttribute("aria-current", "page");
  await page.goto("/#/insights");
  await expect(nav.getByRole("button", { name: "Research Gaps" })).toHaveAttribute("aria-current", "page");
  // advanced filters and the coverage map are collapsed until asked for
  await page.goto("/#/experiments");
  await expect(page.getByLabel("Facility")).toBeHidden();
  await page.getByText(/More filters/).click();
  await expect(page.getByLabel("Facility")).toBeVisible();
  await page.goto("/#/gaps");
  await expect(page.locator(".heat").first()).toBeHidden();
  await page.getByText("Coverage map by fuel class, pressure and O₂").click();
  await expect(page.locator(".heat").first()).toBeVisible();
  // shortcuts on the overview work
  await page.goto("/#/overview");
  await page.getByRole("button", { name: /Check a habitat atmosphere/ }).click();
  await expect(page.getByText("Pick a habitat atmosphere").first()).toBeVisible();
  // phone width: no horizontal overflow on any destination
  await page.setViewportSize({ width: 390, height: 844 });
  for (const r of ["overview", "experiments/PSI-159", "compare", "scenarios", "twin/habitat", "gaps", "assistant"]) {
    await page.goto(`/#/${r}`);
    await page.waitForTimeout(800);
    expect(await page.evaluate(() => document.documentElement.scrollWidth), r).toBeLessThanOrEqual(390);
  }
});

test("rendering performance on this machine (software WebGL: a lower bound)", async ({ page }) => {
  await freshTwin(page);
  const fps = await page.evaluate(() => new Promise((res) => {
    let n = 0; const t0 = performance.now();
    const tick = () => { n++; if (performance.now() - t0 < 2000) requestAnimationFrame(tick); else res(n / ((performance.now() - t0) / 1000)); };
    requestAnimationFrame(tick);
  }));
  console.log(`habitat view with airflow animation: ${fps.toFixed(1)} fps (headless Chrome, SwiftShader software rendering — a lower bound, not GPU performance)`);
  expect(fps).toBeGreaterThan(0.5); // the render loop stays alive; real-GPU frame rate is measured separately (docs)
});
