"""
File operations for moving/copying photos with undo support.
"""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Callable
import shutil
import logging

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


@dataclass
class FileOperation:
    """Represents a single file operation for history/undo."""
    operation_type: str  # 'move' or 'copy'
    source_path: Path
    destination_path: Path
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class OperationBatch:
    """A batch of operations that can be undone together."""
    operations: List[FileOperation] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    description: str = ""
    
    @property
    def successful_count(self) -> int:
        return sum(1 for op in self.operations if op.success)
    
    @property
    def failed_count(self) -> int:
        return sum(1 for op in self.operations if not op.success)


class FileOperations(QObject):
    """Handles file move/copy operations with undo support."""
    
    # Signals for progress reporting
    progress_updated = Signal(int, int)  # current, total
    operation_completed = Signal(OperationBatch)
    operation_error = Signal(str)
    
    def __init__(self, max_history: int = 50):
        super().__init__()
        self.history: List[OperationBatch] = []
        self.max_history = max_history
    
    def move_files(
        self,
        file_destinations: List[tuple],  # List of (source_path, dest_path)
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> OperationBatch:
        """
        Move multiple files to their destinations.
        
        Args:
            file_destinations: List of (source_path, destination_path) tuples
            progress_callback: Optional callback for progress updates
            
        Returns:
            OperationBatch with results
        """
        batch = OperationBatch(description=f"Move {len(file_destinations)} files")
        
        for i, (source, dest) in enumerate(file_destinations):
            source_path = Path(source)
            dest_path = Path(dest)
            
            operation = self._move_single_file(source_path, dest_path)
            batch.operations.append(operation)
            
            if progress_callback:
                progress_callback(i + 1, len(file_destinations))
            self.progress_updated.emit(i + 1, len(file_destinations))
        
        self._add_to_history(batch)
        self.operation_completed.emit(batch)
        return batch
    
    def copy_files(
        self,
        file_destinations: List[tuple],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> OperationBatch:
        """
        Copy multiple files to their destinations.
        
        Args:
            file_destinations: List of (source_path, destination_path) tuples
            progress_callback: Optional callback for progress updates
            
        Returns:
            OperationBatch with results
        """
        batch = OperationBatch(description=f"Copy {len(file_destinations)} files")
        
        for i, (source, dest) in enumerate(file_destinations):
            source_path = Path(source)
            dest_path = Path(dest)
            
            operation = self._copy_single_file(source_path, dest_path)
            batch.operations.append(operation)
            
            if progress_callback:
                progress_callback(i + 1, len(file_destinations))
            self.progress_updated.emit(i + 1, len(file_destinations))
        
        self._add_to_history(batch)
        self.operation_completed.emit(batch)
        return batch
    
    def _move_single_file(self, source: Path, dest: Path) -> FileOperation:
        """Move a single file."""
        operation = FileOperation(
            operation_type='move',
            source_path=source,
            destination_path=dest
        )
        
        try:
            # Create destination directory if needed
            dest.parent.mkdir(parents=True, exist_ok=True)
            
            # Handle filename conflicts
            final_dest = self._resolve_conflict(dest)
            operation.destination_path = final_dest
            
            # Move the file
            shutil.move(str(source), str(final_dest))
            operation.success = True
            logger.info(f"Moved: {source} -> {final_dest}")
            
        except Exception as e:
            operation.success = False
            operation.error_message = str(e)
            logger.error(f"Failed to move {source}: {e}")
        
        return operation
    
    def _copy_single_file(self, source: Path, dest: Path) -> FileOperation:
        """Copy a single file."""
        operation = FileOperation(
            operation_type='copy',
            source_path=source,
            destination_path=dest
        )
        
        try:
            # Create destination directory if needed
            dest.parent.mkdir(parents=True, exist_ok=True)
            
            # Handle filename conflicts
            final_dest = self._resolve_conflict(dest)
            operation.destination_path = final_dest
            
            # Copy the file
            shutil.copy2(str(source), str(final_dest))
            operation.success = True
            logger.info(f"Copied: {source} -> {final_dest}")
            
        except Exception as e:
            operation.success = False
            operation.error_message = str(e)
            logger.error(f"Failed to copy {source}: {e}")
        
        return operation
    
    def _resolve_conflict(self, dest: Path) -> Path:
        """Resolve filename conflicts by appending a number."""
        if not dest.exists():
            return dest
        
        base = dest.stem
        ext = dest.suffix
        parent = dest.parent
        
        counter = 1
        while True:
            new_name = f"{base}_{counter}{ext}"
            new_path = parent / new_name
            if not new_path.exists():
                return new_path
            counter += 1
    
    def undo_last(self) -> Optional[OperationBatch]:
        """
        Undo the last batch of operations.
        
        Returns:
            The undone batch, or None if nothing to undo
        """
        if not self.history:
            return None
        
        batch = self.history.pop()
        undo_batch = OperationBatch(description=f"Undo: {batch.description}")
        
        # Process in reverse order
        for operation in reversed(batch.operations):
            if not operation.success:
                continue
                
            if operation.operation_type == 'move':
                # Move back to original location
                undo_op = self._move_single_file(
                    operation.destination_path,
                    operation.source_path
                )
                undo_batch.operations.append(undo_op)
                
            elif operation.operation_type == 'copy':
                # Delete the copy
                try:
                    operation.destination_path.unlink()
                    undo_op = FileOperation(
                        operation_type='delete',
                        source_path=operation.destination_path,
                        destination_path=operation.destination_path,
                        success=True
                    )
                except Exception as e:
                    undo_op = FileOperation(
                        operation_type='delete',
                        source_path=operation.destination_path,
                        destination_path=operation.destination_path,
                        success=False,
                        error_message=str(e)
                    )
                undo_batch.operations.append(undo_op)
        
        return undo_batch
    
    def _add_to_history(self, batch: OperationBatch):
        """Add batch to history, enforcing max size."""
        self.history.append(batch)
        while len(self.history) > self.max_history:
            self.history.pop(0)
    
    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self.history) > 0
    
    def clear_history(self):
        """Clear operation history."""
        self.history.clear()
