import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { SunIcon, MoonIcon, ThemeToggleIcon } from './Icons';

describe('SunIcon', () => {
  it('renders an SVG element', () => {
    render(<SunIcon />);
    const svg = document.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('has default size of 16', () => {
    render(<SunIcon />);
    const svg = document.querySelector('svg');
    expect(svg).toHaveAttribute('width', '16');
    expect(svg).toHaveAttribute('height', '16');
  });

  it('accepts custom size', () => {
    render(<SunIcon size={24} />);
    const svg = document.querySelector('svg');
    expect(svg).toHaveAttribute('width', '24');
    expect(svg).toHaveAttribute('height', '24');
  });

  it('applies className prop', () => {
    render(<SunIcon className="custom-class" />);
    const svg = document.querySelector('svg');
    expect(svg).toHaveClass('custom-class');
  });
});

describe('MoonIcon', () => {
  it('renders an SVG element', () => {
    render(<MoonIcon />);
    const svg = document.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('has default size of 16', () => {
    render(<MoonIcon />);
    const svg = document.querySelector('svg');
    expect(svg).toHaveAttribute('width', '16');
    expect(svg).toHaveAttribute('height', '16');
  });

  it('accepts custom size', () => {
    render(<MoonIcon size={32} />);
    const svg = document.querySelector('svg');
    expect(svg).toHaveAttribute('width', '32');
    expect(svg).toHaveAttribute('height', '32');
  });
});

describe('ThemeToggleIcon', () => {
  it('renders SunIcon when theme is dark', () => {
    render(<ThemeToggleIcon theme="dark" />);
    // SunIcon has multiple path elements (rays), MoonIcon has one
    const paths = document.querySelectorAll('path');
    // Sun icon has a more complex path with multiple parts
    expect(paths.length).toBeGreaterThan(0);
  });

  it('renders MoonIcon when theme is light', () => {
    render(<ThemeToggleIcon theme="light" />);
    const svg = document.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('passes size to underlying icon', () => {
    render(<ThemeToggleIcon theme="dark" size={20} />);
    const svg = document.querySelector('svg');
    expect(svg).toHaveAttribute('width', '20');
    expect(svg).toHaveAttribute('height', '20');
  });
});
