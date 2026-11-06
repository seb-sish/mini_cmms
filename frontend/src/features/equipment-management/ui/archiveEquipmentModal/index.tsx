"use client";

import ConfirmModal from "@shared/ui/confirmModal";
import { maintenanceScheduleKeys } from "@entities/maintenance-schedule";
import { isEquipmentArchived } from "@entities/equipment";
import { useQueryClient } from "@tanstack/react-query";
import { archiveEquipment } from "@entities/equipment";
import { restoreEquipment } from "@entities/equipment";
import { ButtonAppearance } from "@shared/ui/button";
import { useMutation } from "@tanstack/react-query";
import { equipmentKeys } from "@entities/equipment";
import { FlagAppearance } from "@shared/ui/flag";
import { IEquipment } from "@entities/equipment";
import { getErrorMessage } from "@shared/api";
import { useFlags } from "@shared/ui/flag";
import { ReactElement } from "react";

interface IArchiveEquipmentModalProps {
  equipment: IEquipment;
  onClose: () => void;
}

const ArchiveEquipmentModal = ({
  equipment,
  onClose,
}: IArchiveEquipmentModalProps): ReactElement => {
  const queryClient = useQueryClient();
  const { showFlag } = useFlags();
  const isRestoring: boolean = isEquipmentArchived(equipment);

  const archiveMutation = useMutation({
    mutationFn: () =>
      isRestoring
        ? restoreEquipment(equipment.id)
        : archiveEquipment(equipment.id),
    onSuccess: (updatedEquipment) => {
      queryClient.setQueryData(
        equipmentKeys.detail(updatedEquipment.id),
        updatedEquipment
      );
      queryClient.invalidateQueries({ queryKey: equipmentKeys.lists() });
      queryClient.invalidateQueries({ queryKey: maintenanceScheduleKeys.all });
      showFlag({
        appearance: FlagAppearance.SUCCESS,
        title: isRestoring
          ? "Оборудование восстановлено"
          : "Оборудование перенесено в архив",
        description: updatedEquipment.name,
      });
      onClose();
    },
  });

  const handleConfirm = () => {
    archiveMutation.mutate();
  };

  return (
    <ConfirmModal
      title={isRestoring ? "Восстановить из архива?" : "Перенести в архив?"}
      confirmLabel={isRestoring ? "Восстановить" : "В архив"}
      confirmAppearance={
        isRestoring ? ButtonAppearance.PRIMARY : ButtonAppearance.WARNING
      }
      onConfirm={handleConfirm}
      onClose={onClose}
      isPending={archiveMutation.isPending}
      errorMessage={
        archiveMutation.isError ? getErrorMessage(archiveMutation.error) : null
      }
    >
      {isRestoring ? (
        <p>
          Оборудование вернётся в работу со статусом &quot;Выведено из
          работы&quot;. Графики ТО возобновятся с прежними датами.
        </p>
      ) : (
        <p>
          Архивное оборудование нельзя выбрать для новых заявок и ТО, графики ТО
          приостановятся. История обслуживания сохранится. Архивирование
          невозможно при незавершённых заявках.
        </p>
      )}
    </ConfirmModal>
  );
};

export default ArchiveEquipmentModal;
