import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15

Item {
    id: root

    property var theme
    property var iconLibrary
    property string label: ""
    property string helperText: ""
    property string iconName: ""
    property string value: ""
    property var options: []
    property var optionIcons: ({})
    readonly property real pixelRatio: Screen.devicePixelRatio > 0 ? Screen.devicePixelRatio : 1

    signal valueEdited(string value)

    function currentValue() {
        if (root.value.length > 0) {
            return root.value
        }
        return root.options.length > 0 ? root.options[0] : "Select"
    }

    function optionIcon(optionValue) {
        if (root.optionIcons && root.optionIcons[optionValue]) {
            return root.optionIcons[optionValue]
        }
        return ""
    }

    function popupParent() {
        return popup.parent ? popup.parent : root
    }

    function mapTriggerPoint(offsetY) {
        var target = popupParent()
        var globalPoint = trigger.mapToGlobal(0, offsetY)
        return target.mapFromGlobal(globalPoint.x, globalPoint.y)
    }

    function popupX() {
        var target = popupParent()
        var point = root.mapTriggerPoint(0)
        return Math.max(12, Math.min(point.x, target.width - popup.width - 12))
    }

    function popupHeight() {
        if (popup.implicitHeight > 0) {
            return popup.implicitHeight
        }
        if (popup.contentItem) {
            return popup.contentItem.implicitHeight + popup.topPadding + popup.bottomPadding
        }
        return 0
    }

    function popupY() {
        var target = popupParent()
        var popupHeight = root.popupHeight()
        var belowY = root.mapTriggerPoint(trigger.height + 6).y
        var maxY = Math.max(12, target.height - popupHeight - 12)
        if (belowY <= maxY) {
            return Math.max(12, belowY)
        }

        var aboveY = root.mapTriggerPoint(-popupHeight - 6).y
        return Math.max(12, Math.min(aboveY, maxY))
    }

    Layout.fillWidth: true
    implicitWidth: 620
    implicitHeight: column.implicitHeight

    ColumnLayout {
        id: column
        anchors.fill: parent
        spacing: 6

        Text {
            text: root.label
            color: theme.textWeak
            font.pixelSize: 13
            font.weight: 500
        }

        Rectangle {
            id: trigger
            Layout.fillWidth: true
            implicitHeight: 32
            clip: true
            radius: 8
            color: theme.controlSurface
            border.width: 1
            border.color: theme.controlOutline

            Behavior on color { ColorAnimation { duration: 140 } }
            Behavior on border.color { ColorAnimation { duration: 140 } }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 10

                Image {
                    readonly property string displayIcon: {
                        var optionIconName = root.optionIcon(root.currentValue())
                        return optionIconName.length > 0 ? optionIconName : root.iconName
                    }
                    visible: displayIcon.length > 0
                    source: root.iconLibrary ? root.iconLibrary.svgData(displayIcon, theme.iconBase) : ""
                    sourceSize.width: Math.round(16 * root.pixelRatio)
                    sourceSize.height: Math.round(16 * root.pixelRatio)
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                    Layout.preferredWidth: visible ? 16 : 0
                    Layout.preferredHeight: visible ? 16 : 0
                    Accessible.ignored: true
                }

                Text {
                    Layout.fillWidth: true
                    text: root.currentValue()
                    font.pixelSize: 14
                    color: theme.textStrong
                    elide: Text.ElideRight
                    verticalAlignment: Text.AlignVCenter
                }

                Image {
                    source: root.iconLibrary ? root.iconLibrary.svgData("chevron-down", theme.iconBase) : ""
                    sourceSize.width: Math.round(16 * root.pixelRatio)
                    sourceSize.height: Math.round(16 * root.pixelRatio)
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                    Layout.preferredWidth: 16
                    Layout.preferredHeight: 16
                    Layout.alignment: Qt.AlignVCenter
                    rotation: popup.opened ? 180 : 0

                    Behavior on rotation {
                        NumberAnimation { duration: 140; easing.type: Easing.OutCubic }
                    }
                }
            }

            TapHandler {
                onTapped: {
                    if (popup.opened) {
                        popup.close()
                    } else {
                        popup.open()
                    }
                }
            }
        }

        Popup {
            id: popup
            parent: Overlay.overlay ? Overlay.overlay : root
            x: root.popupX()
            y: root.popupY()
            width: trigger.width
            padding: 4
            closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

            background: Rectangle {
                radius: 10
                color: theme.controlSurface
                border.width: 1
                border.color: theme.controlOutline
            }

            enter: Transition {
                ParallelAnimation {
                    NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 110 }
                    NumberAnimation { property: "scale"; from: 0.98; to: 1.0; duration: 140; easing.type: Easing.OutCubic }
                }
            }

            exit: Transition {
                ParallelAnimation {
                    NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 90 }
                    NumberAnimation { property: "scale"; from: 1.0; to: 0.985; duration: 90; easing.type: Easing.OutCubic }
                }
            }

            contentItem: ListView {
                id: optionList
                implicitHeight: Math.min(contentHeight, 220)
                clip: true
                spacing: 2
                model: root.options

                delegate: Rectangle {
                    width: optionList.width
                    height: 38
                    radius: 6
                    color: delegateArea.containsMouse || root.value === modelData
                        ? theme.surfaceBaseActive
                        : "transparent"

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        spacing: 10

                        Image {
                            readonly property string optionIconName: root.optionIcon(modelData)
                            visible: optionIconName.length > 0
                            source: root.iconLibrary ? root.iconLibrary.svgData(optionIconName, theme.iconBase) : ""
                            sourceSize.width: Math.round(16 * root.pixelRatio)
                            sourceSize.height: Math.round(16 * root.pixelRatio)
                            fillMode: Image.PreserveAspectFit
                            smooth: true
                            Layout.preferredWidth: visible ? 16 : 0
                            Layout.preferredHeight: visible ? 16 : 0
                            Accessible.ignored: true
                        }

                        Text {
                            Layout.fillWidth: true
                            text: modelData
                            color: theme.textStrong
                            font.pixelSize: 14
                            elide: Text.ElideRight
                            verticalAlignment: Text.AlignVCenter
                        }
                    }

                    MouseArea {
                        id: delegateArea
                        anchors.fill: parent
                        hoverEnabled: true

                        onClicked: {
                            root.valueEdited(modelData)
                            popup.close()
                        }
                    }
                }
            }
        }

        Text {
            visible: root.helperText.length > 0
            text: root.helperText
            color: theme.textWeak
            font.pixelSize: 13
            font.weight: 400
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
    }
}
