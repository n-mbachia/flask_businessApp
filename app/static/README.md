# Static Files Structure

This directory contains all static assets for the Profitability App, including CSS, JavaScript, images, and fonts.

## Directory Structure

```
static/
├── css/
│   ├── base.css           # Base styles and resets
│   ├── components/        # Component-specific styles
│   │   ├── buttons.css
│   │   ├── cards.css
│   │   ├── forms.css
│   │   └── navigation.css
│   ├── lib/               # Third-party CSS libraries
│   │   ├── bootstrap.min.css
│   │   └── bootstrap-icons.css
│   ├── pages/             # Page-specific styles
│   │   ├── dashboard.css
│   │   ├── products.css
│   │   └── sales.css
│   └── themes/            # Theme variables and overrides
│       ├── variables.css  # CSS custom properties
│       └── dark-mode.css  # Dark theme overrides
├── img/                   # Image assets
├── js/
│   ├── app.js             # Main application entry point
│   ├── components/        # Reusable UI components
│   │   └── charts/        # Chart components
│   │       ├── base.js    # Base chart configurations
│   │       ├── line.js    # Line chart component
│   │       └── bar.js     # Bar chart component
│   ├── lib/               # Third-party JavaScript libraries
│   │   ├── bootstrap.bundle.min.js
│   │   └── plotly-latest.min.js
│   ├── pages/             # Page-specific JavaScript
│   │   ├── dashboard.js
│   │   ├── products.js
│   │   └── sales.js
│   └── utils/             # Utility functions
│       ├── api.js         # API helpers
│       ├── formatters.js  # Data formatting
│       └── dom.js         # DOM manipulation helpers
└── fonts/                 # Custom fonts (if any)
```

## CSS Architecture

### Base Styles
- `base.css` contains global styles, resets, and utility classes
- Uses CSS custom properties for theming and consistency
- Follows BEM (Block Element Modifier) naming convention

### Component Styles
- Each component has its own CSS file
- Components should be self-contained and reusable
- Use CSS custom properties for theming

### Theme Variables
- All design tokens are defined in `themes/variables.css`
- Colors, typography, spacing, and other design tokens are defined as CSS custom properties
- Dark theme overrides are in `themes/dark-mode.css`

## JavaScript Architecture

### Entry Points
- `app.js` is the main entry point
- Page-specific scripts are loaded as modules

### Components
- Reusable UI components are in the `components` directory
- Each component should be self-contained and follow the Single Responsibility Principle

### Utilities
- Reusable utility functions are in the `utils` directory
- API helpers, formatters, and DOM utilities are separated for better organization

## Best Practices

### CSS
- Use CSS custom properties for theming
- Follow the BEM naming convention
- Keep selectors specific but not overly specific
- Use utility classes for common styles
- Mobile-first approach for responsive design

### JavaScript
- Use ES6+ syntax
- Follow the module pattern
- Keep functions small and focused
- Use async/await for asynchronous operations
- Handle errors appropriately

## Development

### Adding a New Component
1. Create a new CSS file in `css/components/`
2. Create a new JavaScript file in `js/components/` if needed
3. Import the component in the appropriate page script

### Theming
- Update variables in `themes/variables.css`
- Add dark mode overrides in `themes/dark-mode.css`
- Use CSS custom properties for all colors and design tokens

## Build Process

### Production Build
1. Minify CSS and JavaScript
2. Optimize images
3. Generate source maps
4. Version assets for cache busting

### Development
- Use source maps for easier debugging
- Enable CSS source maps in the browser
- Use the browser's developer tools for debugging

## Browser Support
- Latest versions of Chrome, Firefox, Safari, and Edge
- IE 11 is not supported
- Progressive enhancement for older browsers

## Performance
- Lazy load non-critical CSS and JavaScript
- Optimize images
- Use responsive images with srcset and sizes
- Minify and compress assets
- Use HTTP/2 for better performance

## Accessibility
- Use semantic HTML
- Ensure proper color contrast
- Add ARIA attributes where necessary
- Test with screen readers
- Keyboard navigation support

## License

This project is proprietary and confidential. All rights reserved.
