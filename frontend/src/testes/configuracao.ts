import "@testing-library/jest-dom/vitest";

// O jsdom não desenha em canvas e reclama a cada tentativa: sem canvas, o céu fica só escuro
HTMLCanvasElement.prototype.getContext = () => null;
