import { describe, expect, it } from "vitest";

import { blobErrorMessage } from "../pdf";

/**
 * With `responseType: "blob"` the error body is a Blob, so the usual
 * `err.response.data.detail` is undefined and the user is shown
 * "Request failed with status code 401" — which tells them nothing.
 */
describe("blobErrorMessage", () => {
  it("reads the detail back out of a JSON blob body", async () => {
    const body = new Blob([JSON.stringify({ detail: "Quotation not found." })], {
      type: "application/json",
    });
    expect(await blobErrorMessage({ response: { status: 404, data: body } }))
      .toBe("Quotation not found.");
  });

  it("explains a 401 in words a cashier can act on", async () => {
    const msg = await blobErrorMessage({
      response: { status: 401, data: new Blob(["{}"]) },
    });
    expect(msg).toMatch(/session has expired/i);
  });

  it("explains a 403 as a permissions problem, not a failure", async () => {
    const msg = await blobErrorMessage({ response: { status: 403, data: new Blob(["{}"]) } });
    expect(msg).toMatch(/role does not have access/i);
  });

  it("handles a plain JSON body too", async () => {
    expect(await blobErrorMessage({ response: { status: 400, data: { detail: "Nope." } } }))
      .toBe("Nope.");
  });

  it("does not choke on an HTML error page", async () => {
    const body = new Blob(["<html>Server Error</html>"], { type: "text/html" });
    expect(await blobErrorMessage({ response: { status: 500, data: body } }, "Fallback."))
      .toBe("Fallback.");
  });

  it("falls back to the error's own message when there is no response", async () => {
    expect(await blobErrorMessage(new Error("Network Error"))).toBe("Network Error");
  });
});
