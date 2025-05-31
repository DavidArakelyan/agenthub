// /Users/davida/workspace/agenthub/services/frontend/src/prismjs-custom.d.ts
// This file provides type declarations for Prism.js components
// that are imported directly, so TypeScript does not complain about
// missing type information.

declare module 'prismjs/components/prism-python' {
    const language: any; // You can replace 'any' with Prism.Grammar if @types/prismjs provides it and it's suitable
    export default language;
}

declare module 'prismjs/components/prism-cpp' {
    const language: any; // You can replace 'any' with Prism.Grammar
    export default language;
}

declare module 'prismjs/components/prism-c' {
    const language: any; // You can replace 'any' with Prism.Grammar
    export default language;
}

declare module 'prismjs/components/prism-java' {
    const language: any; // You can replace 'any' with Prism.Grammar
    export default language;
}
