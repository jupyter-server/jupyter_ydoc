/* -----------------------------------------------------------------------------
| Copyright (c) Jupyter Development Team.
| Distributed under the terms of the Modified BSD License.
|----------------------------------------------------------------------------*/

import type { JSONValue } from '@lumino/coreutils';
import type { ISignal } from '@lumino/signaling';

/**
 * Generic annotation change
 */
export type AnnotationsChange<T> = {
  oldValue?: T;
  newValue?: T;
};

/**
 * Annotation interface.
 */
export interface IAnnotation {
  sender: string;
  pos: JSONValue;
  content: JSONValue;
}

/**
 * Annotations interface.
 * This interface must be implemented by the shared documents that want
 * to include annotations.
 */
export interface IAnnotations<T extends IAnnotation> {
  /**
   * The annotation changed signal.
   */
  readonly annotationChanged: ISignal<this, AnnotationsChange<T>>;

  /**
   * Return an iterator that yields every annotation key.
   */
  readonly annotations: Array<string>;

  /**
   * Get the value for an annotation
   *
   * @param key Key to get
   */
  getAnnotation(key: string): T | undefined;

  /**
   * Set the value of an annotation
   *
   * @param key Key to set
   * @param value New value
   */
  setAnnotation(key: string, value: T): void;

  /**
   * Update the value of an existing annotation
   *
   * @param key Key to update
   * @param value New value
   */
  updateAnnotation(key: string, value: T): void;

  /**
   * Delete an annotation
   *
   * @param key Key to delete
   */
  deleteAnnotation(key: string): void;
}
