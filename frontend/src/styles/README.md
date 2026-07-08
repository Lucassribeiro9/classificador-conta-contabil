# Tokens Visuais

Use `visualTokens` como fonte central para valores compartilhados entre
Tailwind e componentes.

Direcao aprovada:

- base branca: `#ffffff`;
- marca: `#007693`;
- apoio escuro: `#004E61`;
- cinzas neutros para texto, bordas e fundo;
- UI operacional compacta, com raio pequeno e pouca decoracao.

Evite criar cores soltas nas telas. Quando uma nova cor ou dimensao visual for
necessaria, adicione primeiro em `tokens.ts` e depois consuma via Tailwind ou
CSS global.
