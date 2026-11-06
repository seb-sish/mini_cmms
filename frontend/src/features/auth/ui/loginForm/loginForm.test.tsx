import LoginForm from "./index";
import userEvent from "@testing-library/user-event";
import { QueryClientProvider } from "@tanstack/react-query";
import { QueryClient } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { screen } from "@testing-library/react";

const renderLoginForm = (onSuccess = vi.fn()) => {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <LoginForm onSuccess={onSuccess} />
    </QueryClientProvider>
  );

  return onSuccess;
};

const jsonResponse = (status: number, body: unknown): Response =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });

describe("LoginForm", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("validates fields before sending request", async () => {
    renderLoginForm();

    await userEvent.click(screen.getByRole("button", { name: "Войти" }));

    expect(screen.getAllByText("Обязательное поле.")).toHaveLength(2);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("sends trimmed login to BFF and reports success", async () => {
    const user = { id: "1", login: "operator1" };
    const onSuccess = renderLoginForm();

    fetchMock.mockResolvedValue(
      jsonResponse(200, { user, expires_at: "2026-10-29T21:00:00Z" })
    );

    await userEvent.type(screen.getByLabelText(/Логин/), "  operator1 ");
    await userEvent.type(screen.getByLabelText(/Пароль/), "Secret-Pass-1");
    await userEvent.click(screen.getByRole("button", { name: "Войти" }));

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/login",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ login: "operator1", password: "Secret-Pass-1" }),
      })
    );
    expect(onSuccess).toHaveBeenCalledWith({
      user,
      expires_at: "2026-10-29T21:00:00Z",
    });
  });

  it("shows neutral message on invalid credentials", async () => {
    renderLoginForm();
    fetchMock.mockResolvedValue(
      jsonResponse(401, { status: 401, code: "INVALID_CREDENTIALS" })
    );

    await userEvent.type(screen.getByLabelText(/Логин/), "operator1");
    await userEvent.type(screen.getByLabelText(/Пароль/), "wrong-password");
    await userEvent.click(screen.getByRole("button", { name: "Войти" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Неверный логин или пароль."
    );
  });
});
