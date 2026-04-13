pragma ComponentBehavior: Bound

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
    property var optionLabels: ({})
    property var optionIcons: ({})
    readonly property real pixelRatio: Screen.devicePixelRatio > 0 ? Screen.devicePixelRatio : 1

    signal valueEdited(string value)

    function indexForValue() {
        var index = root.options.indexOf(root.value)
        if (index >= 0) {
            return index
        }
        return root.options.length > 0 ? 0 : -1
    }

    function currentValue() {
        return combo.currentIndex >= 0 ? root.optionLabel(root.options[combo.currentIndex]) : "Select"
    }

    function optionLabel(optionValue) {
        if (root.optionLabels && root.optionLabels[optionValue]) {
            return root.optionLabels[optionValue]
        }
        return optionValue
    }

    function optionIcon(optionValue) {
        if (root.optionIcons && root.optionIcons[optionValue]) {
            return root.optionIcons[optionValue]
        }
        return ""
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
            color: root.theme.textWeak
            font.pixelSize: 13
            font.weight: 500
        }

        ComboBox {
            id: combo
            Layout.fillWidth: true
            implicitHeight: 32
            model: root.options
            currentIndex: root.indexForValue()
            hoverEnabled: true
            Accessible.name: root.label

            onActivated: (index) => root.valueEdited(root.options[index])

            background: Rectangle {
                radius: 8
                color: combo.pressed
                    ? root.theme.surfaceBaseActive
                    : (combo.hovered ? root.theme.surfaceBaseHover : root.theme.controlSurface)
                border.width: 1
                border.color: combo.visualFocus || combo.popup.visible
                    ? root.theme.borderSelected
                    : root.theme.controlOutline

                Behavior on color { ColorAnimation { duration: 140 } }
                Behavior on border.color { ColorAnimation { duration: 140 } }
            }

            indicator: Image {
                source: root.iconLibrary ? root.iconLibrary.svgData("chevron-down", root.theme.iconBase) : ""
                width: 16
                height: 16
                sourceSize.width: Math.round(16 * root.pixelRatio)
                sourceSize.height: Math.round(16 * root.pixelRatio)
                fillMode: Image.PreserveAspectFit
                smooth: true
                x: Math.round(combo.width - width - 12)
                y: Math.round((combo.height - height) / 2)
                rotation: combo.popup.visible ? 180 : 0
                Accessible.ignored: true

                Behavior on rotation {
                    NumberAnimation { duration: 140; easing.type: Easing.OutCubic }
                }
            }

            contentItem: Item {
                implicitHeight: 32

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 34
                    spacing: 10

                    Image {
                        readonly property string displayIcon: {
                            var selectedValue = combo.currentIndex >= 0 ? root.options[combo.currentIndex] : ""
                            var optionIconName = root.optionIcon(selectedValue)
                            return optionIconName.length > 0 ? optionIconName : root.iconName
                        }
                        visible: displayIcon.length > 0
                        source: root.iconLibrary ? root.iconLibrary.svgData(displayIcon, root.theme.iconBase) : ""
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
                        color: root.theme.textStrong
                        font.pixelSize: 14
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }

            delegate: ItemDelegate {
                id: delegateRoot
                required property int index
                required property string modelData
                width: combo.width - 8
                implicitHeight: 38
                highlighted: combo.highlightedIndex === index
                hoverEnabled: true
                padding: 0

                background: Rectangle {
                    radius: 6
                    color: delegateRoot.highlighted || combo.currentIndex === delegateRoot.index
                        ? root.theme.surfaceBaseActive
                        : "transparent"
                }

                contentItem: RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    spacing: 10

                    Image {
                        readonly property string optionIconName: root.optionIcon(delegateRoot.modelData)
                        visible: optionIconName.length > 0
                        source: root.iconLibrary ? root.iconLibrary.svgData(optionIconName, root.theme.iconBase) : ""
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
                        text: root.optionLabel(delegateRoot.modelData)
                        color: root.theme.textStrong
                        font.pixelSize: 14
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }

            popup: Popup {
                y: combo.height + 6
                width: combo.width
                margins: 12
                padding: 4
                modal: true
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                Overlay.modal: Rectangle {
                    color: root.theme.surfaceBase
                }

                background: Rectangle {
                    radius: 10
                    color: root.theme.controlSurface
                    border.width: 1
                    border.color: root.theme.controlOutline
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
                    clip: true
                    implicitHeight: Math.min(contentHeight, 220)
                    model: combo.popup.visible ? combo.delegateModel : null
                    currentIndex: combo.highlightedIndex
                    spacing: 2
                    ScrollIndicator.vertical: ScrollIndicator {}
                }
            }
        }

        Text {
            visible: root.helperText.length > 0
            text: root.helperText
            color: root.theme.textWeak
            font.pixelSize: 13
            font.weight: 400
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
    }
}
