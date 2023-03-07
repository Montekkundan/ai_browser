# Copyright (C) 2022 The Qt Company Ltd.
# SPDX-License-Identifier: LicenseRef-Qt-Commercial OR BSD-3-Clause

from functools import partial

from bookmarkwidget import BookmarkWidget
from webengineview import WebEngineView
from historywindow import HistoryWindow
from PySide6.QtCore import Qt, QUrl, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMenu, QTabBar, QTabWidget
from PySide6.QtWebEngineCore import QWebEngineDownloadRequest, QWebEnginePage


# TODO: Expected Release November 2023
# from PySide6.QtWebEngineWidgets import QWebEnginePage


class BrowserTabWidget(QTabWidget):
    """Enables having several tabs with QWebEngineView."""

    url_changed = Signal(QUrl)
    enabled_changed = Signal(QWebEnginePage.WebAction, bool)
    download_requested = Signal(QWebEngineDownloadRequest)

    def __init__(self, window_factory_function):
        super().__init__()
        self.added_url = None
        self.setTabsClosable(True)
        self._window_factory_function = window_factory_function
        self._webengineviews = []
        self._history_windows = {}  # map WebengineView to HistoryWindow
        self.currentChanged.connect(self._current_changed)
        self.tabCloseRequested.connect(self.handle_tab_close_request)
        self._actions_enabled = {}
        for web_action in WebEngineView.web_actions():
            self._actions_enabled[web_action] = False

        tab_bar = self.tabBar()
        tab_bar.setSelectionBehaviorOnRemove(QTabBar.SelectPreviousTab)
        tab_bar.setContextMenuPolicy(Qt.CustomContextMenu)
        tab_bar.customContextMenuRequested.connect(self._handle_tab_context_menu)

    def add_browser_tab(self, url=''):
        factory_func = partial(BrowserTabWidget.add_browser_tab, self)
        web_engine_view = WebEngineView(factory_func,
                                        self._window_factory_function)
        index = self.count()
        self._webengineviews.append(web_engine_view)
        self.added_url = url

        page = web_engine_view.page()
        if url != '':
            web_engine_view.setUrl(url)
            page = web_engine_view.page()
            page.titleChanged.connect(self._update_tab_title)
        page.titleChanged.connect(self._title_changed)
        page.iconChanged.connect(self._icon_changed)
        page.profile().downloadRequested.connect(self._download_requested)
        web_engine_view.urlChanged.connect(self._url_changed)
        web_engine_view.enabled_changed.connect(self._enabled_changed)
        title = f'{page.title()}'
        self.addTab(web_engine_view, title)
        self.setCurrentIndex(index)
        return web_engine_view

    def _update_tab_title(self, title):
        index = self.currentIndex()
        self.setTabText(index, f'{title} ')
    def load(self, url):
        index = self.currentIndex()
        if index >= 0 and url.isValid():
            self._webengineviews[index].setUrl(url)

    def find(self, needle, flags):
        index = self.currentIndex()
        if index >= 0:
            self._webengineviews[index].page().findText(needle, flags)

    def url(self):
        index = self.currentIndex()
        return self._webengineviews[index].url() if index >= 0 else QUrl()

    @Slot(QUrl)
    def _url_changed(self, url):
        index = self.currentIndex()
        if index >= 0 and self._webengineviews[index] == self.sender():
            self.url_changed.emit(url)

    @Slot(str)
    def _title_changed(self, title):
        index = self._index_of_page(self.sender())
        if index >= 0:
            self.setTabText(index, BookmarkWidget.short_title(title))

    @Slot(QIcon)
    def _icon_changed(self, icon):
        index = self._index_of_page(self.sender())
        if (index >= 0):
            self.setTabIcon(index, icon)

    @Slot(object, bool)
    def _enabled_changed(self, web_action, enabled):
        index = self.currentIndex()
        if index >= 0 and self._webengineviews[index] == self.sender():
            self._check_emit_enabled_changed(web_action, enabled)

    def _check_emit_enabled_changed(self, web_action, enabled):
        if enabled != self._actions_enabled[web_action]:
            self._actions_enabled[web_action] = enabled
            self.enabled_changed.emit(web_action, enabled)

    def _current_changed(self, index):
        self._update_actions(index)
        self.url_changed.emit(self.url())

    def _update_actions(self, index):
        if 0 <= index < len(self._webengineviews):
            view = self._webengineviews[index]
            for web_action in WebEngineView.web_actions():
                enabled = view.is_web_action_enabled(web_action)
                self._check_emit_enabled_changed(web_action, enabled)

    def back(self):
        self._trigger_action(QWebEnginePage.Back)

    def forward(self):
        self._trigger_action(QWebEnginePage.Forward)

    def reload(self):
        self._trigger_action(QWebEnginePage.Reload)

    def undo(self):
        self._trigger_action(QWebEnginePage.Undo)

    def redo(self):
        self._trigger_action(QWebEnginePage.Redo)

    def cut(self):
        self._trigger_action(QWebEnginePage.Cut)

    def copy(self):
        self._trigger_action(QWebEnginePage.Copy)

    def paste(self):
        self._trigger_action(QWebEnginePage.Paste)

    def select_all(self):
        self._trigger_action(QWebEnginePage.SelectAll)

    def show_history(self):
        index = self.currentIndex()
        if index >= 0:
            webengineview = self._webengineviews[index]
            history_window = self._history_windows.get(webengineview)
            if not history_window:
                history = webengineview.page().history()
                history_window = HistoryWindow(history, self)
                history_window.open_url.connect(self.load)
                history_window.setWindowFlags(history_window.windowFlags()
                                              | Qt.Window)
                history_window.setWindowTitle('History')
                self._history_windows[webengineview] = history_window
            else:
                history_window.refresh()
            history_window.show()
            history_window.raise_()

    def zoom_factor(self):
        return self._webengineviews[0].zoomFactor() if self._webengineviews else 1.0

    def set_zoom_factor(self, z):
        for w in self._webengineviews:
            w.setZoomFactor(z)

    def _handle_tab_context_menu(self, point):
        index = self.tabBar().tabAt(point)
        if index < 0:
            return
        tab_count = len(self._webengineviews)
        context_menu = QMenu()
        duplicate_tab_action = context_menu.addAction("Duplicate Tab")
        close_other_tabs_action = context_menu.addAction("Close Other Tabs")
        close_other_tabs_action.setEnabled(tab_count > 1)
        close_tabs_to_the_right_action = context_menu.addAction("Close Tabs to the Right")
        close_tabs_to_the_right_action.setEnabled(index < tab_count - 1)
        close_tab_action = context_menu.addAction("&Close Tab")
        chosen_action = context_menu.exec(self.tabBar().mapToGlobal(point))
        if chosen_action == duplicate_tab_action:
            current_url = self.url()
            self.add_browser_tab().load(current_url)
        elif chosen_action == close_other_tabs_action:
            for t in range(tab_count - 1, -1, -1):
                if t != index:
                    self.handle_tab_close_request(t)
        elif chosen_action == close_tabs_to_the_right_action:
            for t in range(tab_count - 1, index, -1):
                self.handle_tab_close_request(t)
        elif chosen_action == close_tab_action:
            self.handle_tab_close_request(index)

    def handle_tab_close_request(self, index):
        if (index >= 0 and self.count() > 1):
            webengineview = self._webengineviews[index]
            if self._history_windows.get(webengineview):
                del self._history_windows[webengineview]
            self._webengineviews.remove(webengineview)
            widget = self.widget(index)
            widget.close()
            widget.deleteLater()
            self.removeTab(index)

    def close_current_tab(self):
        self.handle_tab_close_request(self.currentIndex())

    def _trigger_action(self, action):
        index = self.currentIndex()
        if index >= 0:
            self._webengineviews[index].page().triggerAction(action)

    def _index_of_page(self, web_page):
        for p in range(0, len(self._webengineviews)):
            if (self._webengineviews[p].page() == web_page):
                return p
        return -1

    @Slot(QWebEngineDownloadRequest)
    def _download_requested(self, item):
        self.download_requested.emit(item)
