import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ConfirmDialog } from '../components/ConfirmDialog';

describe('ConfirmDialog', () => {
  it('renders title and message', () => {
    render(
      <ConfirmDialog
        title="Delete Item"
        message="Are you sure you want to delete this item?"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );
    expect(screen.getByText('Delete Item')).toBeInTheDocument();
    expect(screen.getByText('Are you sure you want to delete this item?')).toBeInTheDocument();
  });

  it('renders default button labels', () => {
    render(
      <ConfirmDialog
        title="Confirm Dialog"
        message="Proceed?"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Confirm' })).toBeInTheDocument();
  });

  it('renders custom button labels', () => {
    render(
      <ConfirmDialog
        title="Delete"
        message="Really?"
        confirmLabel="Yes, Delete"
        cancelLabel="No, Keep"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );
    expect(screen.getByRole('button', { name: 'Yes, Delete' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'No, Keep' })).toBeInTheDocument();
  });

  it('calls onConfirm when confirm button clicked', () => {
    const onConfirm = vi.fn();
    render(
      <ConfirmDialog
        title="Are You Sure?"
        message="OK?"
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it('calls onCancel when cancel button clicked', () => {
    const onCancel = vi.fn();
    render(
      <ConfirmDialog
        title="Cancel?"
        message="OK?"
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('calls onCancel when overlay clicked', () => {
    const onCancel = vi.fn();
    render(
      <ConfirmDialog
        title="Test"
        message="Test message"
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />
    );
    const overlay = document.querySelector('.modal-overlay');
    fireEvent.click(overlay!);
    expect(onCancel).toHaveBeenCalled();
  });

  it('calls onCancel on Escape key', () => {
    const onCancel = vi.fn();
    render(
      <ConfirmDialog
        title="Test"
        message="Test message"
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />
    );
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onCancel).toHaveBeenCalled();
  });

  it('does not call onCancel for non-Escape keys', () => {
    const onCancel = vi.fn();
    render(
      <ConfirmDialog
        title="Test"
        message="Test"
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />
    );
    fireEvent.keyDown(window, { key: 'Enter' });
    expect(onCancel).not.toHaveBeenCalled();
  });

  it('applies danger class to confirm button', () => {
    render(
      <ConfirmDialog
        title="Danger"
        message="This is dangerous"
        danger
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );
    const confirmBtn = screen.getByRole('button', { name: 'Confirm' });
    expect(confirmBtn.className).toContain('btn-danger');
  });

  it('uses btn-confirm class for non-danger', () => {
    render(
      <ConfirmDialog
        title="Safe"
        message="This is safe"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );
    const confirmBtn = screen.getByRole('button', { name: 'Confirm' });
    expect(confirmBtn.className).toContain('btn-confirm');
  });

  it('cleans up Escape listener on unmount', () => {
    const onCancel = vi.fn();
    const { unmount } = render(
      <ConfirmDialog
        title="Test"
        message="Test"
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />
    );
    unmount();
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onCancel).not.toHaveBeenCalled();
  });
});
