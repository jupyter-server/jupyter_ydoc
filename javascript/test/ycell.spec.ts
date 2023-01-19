// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

import { IMapChange, YCodeCell, YNotebook } from '../src';

describe('@jupyter/ydoc', () => {
  describe('YCell standalone', () => {
    test('should set source', () => {
      const codeCell = YCodeCell.create();
      codeCell.setSource('test');
      expect(codeCell.getSource()).toBe('test');
      codeCell.dispose();
    });

    test('should update source', () => {
      const codeCell = YCodeCell.create();
      codeCell.setSource('test');
      codeCell.updateSource(0, 0, 'hello');
      expect(codeCell.getSource()).toBe('hellotest');
      codeCell.dispose();
    });

    test('should get metadata', () => {
      const cell = YCodeCell.create();
      const metadata = {
        collapsed: true,
        editable: false,
        name: 'cell-name'
      };

      cell.setMetadata(metadata);

      expect(cell.metadata).toEqual({
        ...metadata,
        jupyter: { outputs_hidden: true }
      });
      cell.dispose();
    });

    test('should get all metadata', () => {
      const cell = YCodeCell.create();
      const metadata = {
        jupyter: { outputs_hidden: true },
        editable: false,
        name: 'cell-name'
      };

      cell.setMetadata(metadata);

      expect(cell.getMetadata()).toEqual({ ...metadata, collapsed: true });
      cell.dispose();
    });

    test('should get one metadata', () => {
      const cell = YCodeCell.create();
      const metadata = {
        collapsed: true,
        editable: false,
        name: 'cell-name'
      };

      cell.setMetadata(metadata);

      expect(cell.getMetadata('editable')).toEqual(metadata.editable);
      cell.dispose();
    });

    it.each([null, undefined, 1, true, 'string', { a: 1 }, [1, 2]])(
      'should get single metadata %s',
      value => {
        const cell = YCodeCell.create();
        const metadata = {
          collapsed: true,
          editable: false,
          name: 'cell-name',
          test: value
        };

        cell.setMetadata(metadata);

        expect(cell.getMetadata('test')).toEqual(value);
        cell.dispose();
      }
    );

    test('should set one metadata', () => {
      const cell = YCodeCell.create();
      const metadata = {
        collapsed: true,
        editable: false,
        name: 'cell-name'
      };

      cell.setMetadata(metadata);
      cell.setMetadata('test', 'banana');

      expect(cell.getMetadata('test')).toEqual('banana');
      cell.dispose();
    });

    test('should emit all metadata changes', () => {
      const notebook = YNotebook.create();

      const metadata = {
        collapsed: true,
        editable: false,
        name: 'cell-name'
      };

      const changes: IMapChange[] = [];
      notebook.metadataChanged.connect((_, c) => {
        changes.push(c);
      });
      notebook.metadata = metadata;

      expect(changes).toHaveLength(3);
      expect(changes).toEqual([
        {
          type: 'add',
          key: 'collapsed',
          newValue: metadata.collapsed,
          oldValue: undefined
        },
        {
          type: 'add',
          key: 'editable',
          newValue: metadata.editable,
          oldValue: undefined
        },
        {
          type: 'add',
          key: 'name',
          newValue: metadata.name,
          oldValue: undefined
        }
      ]);

      notebook.dispose();
    });

    test('should emit a add metadata change', () => {
      const cell = YCodeCell.create();
      const metadata = {
        collapsed: true,
        editable: false,
        name: 'cell-name'
      };
      cell.metadata = metadata;

      const changes: IMapChange[] = [];
      cell.metadataChanged.connect((_, c) => {
        changes.push(c);
      });
      cell.setMetadata('test', 'banana');

      try {
        expect(changes).toHaveLength(1);
        expect(changes).toEqual([
          { type: 'add', key: 'test', newValue: 'banana', oldValue: undefined }
        ]);
      } finally {
        cell.dispose();
      }
    });

    test('should emit a delete metadata change', () => {
      const cell = YCodeCell.create();
      const metadata = {
        collapsed: true,
        editable: false,
        name: 'cell-name'
      };
      cell.metadata = metadata;

      const changes: IMapChange[] = [];
      cell.setMetadata('test', 'banana');

      cell.metadataChanged.connect((_, c) => {
        changes.push(c);
      });
      cell.deleteMetadata('test');

      try {
        expect(changes).toHaveLength(1);
        expect(changes).toEqual([
          {
            type: 'remove',
            key: 'test',
            newValue: undefined,
            oldValue: 'banana'
          }
        ]);
      } finally {
        cell.dispose();
      }
    });

    test('should emit an update metadata change', () => {
      const cell = YCodeCell.create();
      const metadata = {
        collapsed: true,
        editable: false,
        name: 'cell-name'
      };
      cell.metadata = metadata;

      const changes: IMapChange[] = [];
      cell.setMetadata('test', 'banana');

      cell.metadataChanged.connect((_, c) => {
        changes.push(c);
      });
      cell.setMetadata('test', 'orange');

      try {
        expect(changes).toHaveLength(1);
        expect(changes).toEqual([
          {
            type: 'change',
            key: 'test',
            newValue: 'orange',
            oldValue: 'banana'
          }
        ]);
      } finally {
        cell.dispose();
      }
    });
  });
});
