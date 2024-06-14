import os
import re
import shutil
import json
import datetime
import time
import subprocess
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QTextEdit, QPushButton, QFileDialog, QInputDialog, QAction, QMainWindow, QSizePolicy
from PyQt5.QtWidgets import QListWidget, QStyledItemDelegate, QApplication, QStyleOptionViewItem, QStyle
from PyQt5.QtGui import QColorConstants, QColor
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QSize

class CenterAlignedItemDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        option = QStyleOptionViewItem(option)
        self.initStyleOption(option, index)
        option.displayAlignment = Qt.AlignCenter
        painter.setFont(option.font)
        QApplication.style().drawControl(QStyle.CE_ItemViewItem, option, painter)

class EldenRingSaveSwapper(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Elden Ring Save Swapper")
        self.setGeometry(100, 100, 400, 600)  # Changed width and height
        
        self.app_config_file = "elden_ring_save_swapper_config.json"
        self.load_config()

        self.setup_ui()
        
        if not self.app_config or 'setup_complete' not in self.app_config:
            self.initial_setup()
        
        self.refresh_save_list()

    def setup_ui(self):
        widget = QWidget()
        self.setCentralWidget(widget)
        layout = QVBoxLayout()
        widget.setLayout(layout)

        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")

        set_elden_ring_save_action = QAction("Set Elden Ring Save Location", self)
        set_elden_ring_save_action.triggered.connect(self.set_save_location)
        file_menu.addAction(set_elden_ring_save_action)

        set_backup_location_action = QAction("Set Backup Location", self)
        set_backup_location_action.triggered.connect(self.set_backup_location)
        file_menu.addAction(set_backup_location_action)

        run_initial_setup_action = QAction("Run Initial Setup Again", self)
        run_initial_setup_action.triggered.connect(self.initial_setup)
        file_menu.addAction(run_initial_setup_action)

        file_menu.addSeparator()

        create_fresh_save_action = QAction("Create a Fresh Save", self)
        create_fresh_save_action.triggered.connect(self.create_fresh_save)
        file_menu.addAction(create_fresh_save_action)

        add_existing_save_action = QAction("Add an Existing Save", self)
        add_existing_save_action.triggered.connect(self.add_new_save)
        file_menu.addAction(add_existing_save_action)

        rename_save_action = QAction("Rename Save", self)
        rename_save_action.triggered.connect(self.rename_save)
        file_menu.addAction(rename_save_action)

        file_menu.addSeparator()

        open_save_location_action = QAction("Open Save Location", self)
        open_save_location_action.triggered.connect(self.open_save_location)
        file_menu.addAction(open_save_location_action)

        open_backup_location_action = QAction("Open Backup Location", self)
        open_backup_location_action.triggered.connect(self.open_backup_location)
        file_menu.addAction(open_backup_location_action)

        self.current_save_label = QLabel("Currently Loaded Save: ")
        self.current_save_label.setStyleSheet("color: #333; font-size: 24px; font-family: 'Times New Roman', serif; text-align: center;")  # Adjusted alignment to center
        self.current_save_label.setAlignment(QtCore.Qt.AlignCenter)  # Align the text inside QLabel
        layout.addWidget(self.current_save_label)

        self.save_list_widget = QListWidget()
        self.save_list_widget.setStyleSheet("background-color: #333; color: #DDD; font-size: 32px; font-family: 'Times New Roman', serif;")
        layout.addWidget(self.save_list_widget)

        # Create an instance of the custom item delegate
        center_aligned_delegate = CenterAlignedItemDelegate()
        
        # Set the item delegate for the QListWidget
        self.save_list_widget.setItemDelegate(center_aligned_delegate)

        self.output_text_edit = QTextEdit()
        self.output_text_edit.setStyleSheet("background-color: #333; color: #DDD; font-size: 14px; font-family: 'Times New Roman', serif;")
        self.output_text_edit.setReadOnly(True)
        self.output_text_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        layout.addWidget(self.output_text_edit)

        select_save_button = QPushButton("Select Save")
        select_save_button.setStyleSheet("background-color: #777; color: #DDD; font-size: 16px; font-family: 'Times New Roman', serif;")
        select_save_button.clicked.connect(self.select_save)
        layout.addWidget(select_save_button)

        self.update_current_save_label()

    def load_config(self):
        try:
            with open(self.app_config_file, 'r') as f:
                self.app_config = json.load(f)
            
            # Check and set default values if necessary
            if 'save_location' not in self.app_config:
                self.app_config['save_location'] = ""
            if 'backup_location' not in self.app_config:
                self.app_config['backup_location'] = ""
            if 'timestamp_backup_location' not in self.app_config:
                self.app_config['timestamp_backup_location'] = ""
            if 'setup_complete' not in self.app_config:
                self.app_config['setup_complete'] = False

        except FileNotFoundError:
            # Set default values if the file is not found
            self.app_config = {
                'save_location': "",
                'backup_location': "",
                'timestamp_backup_location': "",
                'setup_complete': False
            }

    def save_config(self):
        with open(self.app_config_file, 'w') as f:
            json.dump(self.app_config, f, indent=4)

    def is_elden_ring_running(self):
        try:
            # Use tasklist to check for EldenRing.exe or EAC startup
            processes = subprocess.check_output(["tasklist"], shell=True).decode()
            # Return True if EldenRing.exe is found in the processes list
            return "eldenring.exe" in processes or "start_protected_game.exe" in processes or "EasyAntiCheat_EOS.exe" in processes
        except subprocess.CalledProcessError as e:
            self.update_status("Unable to verify Elden Ring is not running.", 'red')
            return True  # Assume running if there's an error fetching process list.

    def initial_setup(self):
        self.set_save_location()
        self.set_backup_location()
        self.create_swap_directory()
        current_save_name, ok = QInputDialog.getText(self, "Save Name", "Enter a name for the current save:")
        if ok:
            if current_save_name:
                self.app_config['last_used_save'] = current_save_name
            else:
                self.app_config['last_used_save'] = 'Default_Save'

            self.perform_backup(current_save_name, initial=True)

            self.app_config['setup_complete'] = True
            self.save_config()

    def wait_for_file_creation(self, file_path, timeout=10):
        """Wait for a file to be created within a timeout period."""
        start_time = time.time()
        while True:
            if os.path.exists(file_path):
                return True
            elif time.time() - start_time > timeout:
                return False
            time.sleep(1)

    def open_save_location(self):
        save_location = self.app_config.get('save_location', '')
        if save_location and os.path.exists(save_location):
            os.startfile(save_location)
        else:
            self.update_status("Save location is not set or does not exist.", 'red')

    def open_backup_location(self):
        backup_location = self.app_config.get('backup_location', '')
        if backup_location and os.path.exists(backup_location):
            os.startfile(backup_location)
        else:
            self.update_status("Backup location is not set or does not exist.", 'red')


    def perform_backup(self, save_name, initial=False):
        current_save_path = self.app_config['save_location']
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        try:
            for file in os.listdir(current_save_path):
                if file.startswith("ER0000") and (file.endswith(".sl2") or file.endswith(".sl2.bak")):
                    timestamp_backup_file = os.path.join(self.app_config['timestamp_backup_location'], f"{save_name}_{timestamp}_{file}")
                    shutil.copy2(os.path.join(current_save_path, file), timestamp_backup_file)

            if not initial:
                self.cleanup_old_backups(save_name)  # Cleanup old backups after creating a new one
                self.update_status(f"Timestamped backup completed for save: {save_name}.", 'green')
        except Exception as e:
            self.update_status(f"Error during timestamped backup: {str(e)}", 'red')

    def set_save_location(self):
        try:
            directory = QFileDialog.getExistingDirectory(self, "Select Elden Ring Save Location")
            if directory:
                self.app_config['save_location'] = directory
                self.save_config()
        except Exception as e:
            self.update_status(f"Error setting save location: {str(e)}", 'red')

    def set_backup_location(self):
        try:
            directory = QFileDialog.getExistingDirectory(self, "Select Backup Location")
            if directory:
                self.app_config['backup_location'] = directory
                self.app_config['timestamp_backup_location'] = os.path.join(directory, "Timestamped Backups")
                os.makedirs(self.app_config['timestamp_backup_location'], exist_ok=True)
                self.save_config()
        except Exception as e:
            self.update_status(f"Error setting backup location: {str(e)}", 'red')

    def create_swap_directory(self):
        try:
            swap_dir_name = "Elden Ring Save Swapper"
            swap_dir = os.path.join(self.app_config['save_location'], swap_dir_name, "Saves")
            os.makedirs(swap_dir, exist_ok=True)
            self.app_config['swap_directory'] = swap_dir
            self.save_config()
        except Exception as e:
            self.update_status(f"Error creating swap directory: {str(e)}", 'red')

    def refresh_save_list(self):
        try:
            swap_directory = self.app_config.get('swap_directory', '')
            if not os.path.exists(swap_directory):
                os.makedirs(swap_directory, exist_ok=True)
                return

            self.save_list_widget.clear()
            for save in os.listdir(swap_directory):
                self.save_list_widget.addItem(save)
        except Exception as e:
            self.update_status(f"Error refreshing save list: {str(e)}", 'red')

    def update_status(self, message, color):
        self.output_text_edit.setTextColor(QColor(color))
        self.output_text_edit.append(message)

    def update_current_save_label(self):
        if 'last_used_save' in self.app_config:
            current_save = self.app_config['last_used_save']
            self.current_save_label.setText(f"Currently Loaded Save: {current_save}")

    def select_save(self):
        selected_item = self.save_list_widget.currentItem()
        if selected_item:
            save_name = selected_item.text()
            self.swap_save(save_name)
        else:
            self.update_status("No save selected.", 'red')

    def add_new_save(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Elden Ring Save File", filter="Save files (*.sl2)")
        if file_path:
            new_save_name, ok = QInputDialog.getText(self, "New Save Name", "Enter a name for the new save:")
            if ok:
                if new_save_name:
                    self.perform_backup(new_save_name)
                else:
                    self.update_status("No name provided for the new save.", 'red')

    def create_fresh_save(self):
        fresh_save_name, ok = QInputDialog.getText(self, "Fresh Save Name", "Enter a name for the fresh save:")
        if ok:
            if fresh_save_name:
                current_save_name = self.app_config.get('last_used_save', 'Default_Save')
                self.perform_fresh_save(fresh_save_name, current_save_name)
            else:
                self.update_status("No name provided for the fresh save.", 'red')

    def perform_fresh_save(self, fresh_save_name, current_save_name):
        try:
            current_save_path = self.app_config['save_location']

            # Create a directory for the fresh save
            fresh_save_directory = os.path.join(self.app_config['swap_directory'], fresh_save_name)
            os.makedirs(fresh_save_directory, exist_ok=True)

            # Perform backup of the current save
            self.perform_backup(current_save_name)

            # Remove existing save files
            for file in os.listdir(current_save_path):
                if file.startswith("ER0000") and (file.endswith(".sl2") or file.endswith(".sl2.bak")):
                    os.remove(os.path.join(current_save_path, file))
                if file.endswith(".vdf"):
                    os.remove(os.path.join(current_save_path, file))

            # Update app configuration
            self.app_config['last_used_save'] = fresh_save_name
            self.save_config()
            self.update_current_save_label()
            self.refresh_save_list()
            self.update_status(f"Successfully created fresh save: {fresh_save_name}", 'green')
        except Exception as e:
            self.update_status(f"Error performing fresh save: {str(e)}", 'red')

    def rename_save(self):
        selected_item = self.save_list_widget.currentItem()
        if selected_item:
            old_save_name = selected_item.text()
            new_save_name, ok = QInputDialog.getText(self, "Rename Save", "Enter the new name for the save:")
            if ok:
                if not new_save_name or new_save_name.strip() == "":
                    self.update_status("Invalid new save name.", 'red')
                    return

                # Perform a backup before checking if the new save name already exists
                self.perform_backup(old_save_name)

                # Check if the new save name already exists in a case-insensitive manner
                swap_directory = self.app_config['swap_directory']
                for existing_save_name in os.listdir(swap_directory):
                    if new_save_name.lower() == existing_save_name.lower() and old_save_name.lower() != existing_save_name.lower():
                        self.update_status("A save with the new name already exists. Please choose a different name.", 'red')
                        return

                # Proceed with renaming if the new save name is valid and not already taken
                old_save_dir = os.path.join(self.app_config['swap_directory'], old_save_name)
                new_save_dir = os.path.join(self.app_config['swap_directory'], new_save_name)
                
                # Rename the swap folder
                os.rename(old_save_dir, new_save_dir)

                # Update file prefixes within the new save directory
                for file in os.listdir(new_save_dir):
                    old_path = os.path.join(new_save_dir, file)
                    new_file_name = file.replace(old_save_name, new_save_name, 1)
                    new_path = os.path.join(new_save_dir, new_file_name)
                    os.rename(old_path, new_path)

                # If the renamed save is the current save, update the JSON config
                if old_save_name == self.app_config['last_used_save']:
                    self.app_config['last_used_save'] = new_save_name
                    self.save_config()
                    self.update_current_save_label()  # Update the label to reflect the new current save name

                self.update_status(f"Save '{old_save_name}' renamed to '{new_save_name}'.", 'green')
                self.refresh_save_list()
        else:
            self.update_status("No save selected to rename.", 'red')

    def cleanup_old_backups(self, save_name):
        backup_dir = self.app_config['timestamp_backup_location']
        # Pattern to identify relevant backups and extract the timestamp
        pattern = re.compile(rf"^{save_name}_(\d{{4}}-\d{{2}}-\d{{2}}_\d{{2}}-\d{{2}}-\d{{2}})")

        backups = []  # List to hold (filename, timestamp) tuples
        for filename in os.listdir(backup_dir):
            match = pattern.match(filename)
            if match:
                timestamp = datetime.datetime.strptime(match.group(1), "%Y-%m-%d_%H-%M-%S")
                backups.append((filename, timestamp))
        
        # Sort backups by timestamp, oldest first
        backups.sort(key=lambda x: x[1])

        # Remove backups if there are more than three, keeping only the latest three
        while len(backups) > 3:
            oldest_backup = backups.pop(0)[0]  # Remove the oldest
            os.remove(os.path.join(backup_dir, oldest_backup))
            self.update_status(f"Removed old backup: {oldest_backup}", 'green')

    def swap_save(self, save_name):
        if self.is_elden_ring_running():
            self.update_status("Elden Ring is currently running. Please close the game before swapping saves.", 'red')
            return

        current_save_path = self.app_config['save_location']
        current_save_name = self.app_config['last_used_save']
        
        # Step 1: Backup the current save for safety
        self.perform_backup(current_save_name)
        
        # Step 2: Update the swap directory with the current save
        current_swap_folder = os.path.join(self.app_config['swap_directory'], current_save_name)
        os.makedirs(current_swap_folder, exist_ok=True)
        for file in os.listdir(current_save_path):
            if file.startswith("ER0000") and (file.endswith(".sl2") or file.endswith(".sl2.bak")):
                labeled_file = f"{current_save_name}_{file}"
                shutil.copy2(os.path.join(current_save_path, file), os.path.join(current_swap_folder, labeled_file))
        
        # Clear current save files in the game's save location
        for file in os.listdir(current_save_path):
            if file.startswith("ER0000") and (file.endswith(".sl2") or file.endswith(".sl2.bak")):
                os.remove(os.path.join(current_save_path, file))
        
        # Step 3: Copy the selected save to the Elden Ring save directory
        selected_swap_folder = os.path.join(self.app_config['swap_directory'], save_name)
        for file in os.listdir(selected_swap_folder):
            target_file = '_'.join(file.split('_')[1:])  # Remove save name prefix
            shutil.copy2(os.path.join(selected_swap_folder, file), os.path.join(current_save_path, target_file))
        
        # Update the last used save and configuration
        self.app_config['last_used_save'] = save_name
        self.save_config()
        
        # Update UI elements to reflect the changes
        self.update_current_save_label()
        self.refresh_save_list()
        self.update_status(f"Successfully swapped to save: {save_name}", 'green')

if __name__ == "__main__":
    app = QApplication([])
    elden_ring_app = EldenRingSaveSwapper()
    elden_ring_app.show()
    app.exec_()
